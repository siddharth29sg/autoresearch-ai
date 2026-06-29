from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from tavily import TavilyClient
import json

from app.agents.langgraph.state import ResearchGraphState, ScrapedSource, CritiqueResult
from app.core.config import get_settings
from app.core.logging import get_logger
from app.agents.prompts import (
    PLANNER_PROMPT,
    WRITER_PROMPT,
    CRITIC_PROMPT,
)

logger = get_logger(__name__)
settings = get_settings()


# ─── Helpers ──────────────────────────────────────────────

def _get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=settings.groq_api_key,
        model_name=settings.default_model_name,
        temperature=settings.llm_temperature,
        max_tokens=settings.max_tokens,
    )


def _get_tavily() -> TavilyClient:
    return TavilyClient(api_key=settings.tavily_api_key)


def _parse_json_response(raw: str) -> dict:
    """
    Safely parse LLM response that may be wrapped in markdown code fences.
    Fixes the nested JSON string issue — LLMs often wrap JSON in ```json blocks.
    """
    text = raw.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = lines[1:] if lines[0].startswith("```") else lines
        lines = lines[:-1] if lines[-1].strip() == "```" else lines
        text = "\n".join(lines).strip()
    return json.loads(text)


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc
    except Exception:
        return url


# ─── Node 1: Planner ──────────────────────────────────────

async def planner_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Ambiguity → Vector
    Reads:  query, output_format
    Writes: search_plan, search_queries
    """
    research_id = state["research_id"]
    query = state["query"]
    critique = state.get("critique")

    logger.info("planner node started", extra={"research_id": research_id})

    critique_context = ""
    if critique and state.get("loop_count", 0) > 0:
        critique_context = f"""
Previous attempt critique:
{critique['critique_notes']}

Adjust your search strategy based on this feedback.
"""

    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=f"""
Research Query: {query}
Output Format: {state['output_format']}
{critique_context}

Respond in JSON:
{{
    "search_plan": "your reasoning about this query",
    "search_queries": ["query1", "query2", "query3"]
}}
""")
    ])

    try:
        content = _parse_json_response(response.content)
        search_plan = content["search_plan"]
        search_queries = content["search_queries"]
    except (json.JSONDecodeError, KeyError):
        logger.warning(
            "planner returned malformed JSON, using fallback",
            extra={"research_id": research_id}
        )
        search_plan = f"Direct search for: {query}"
        search_queries = [query]

    logger.info(
        "planner node completed",
        extra={"research_id": research_id, "query_count": len(search_queries)}
    )

    return {
        "search_plan": search_plan,
        "search_queries": search_queries,
        "loop_count": state.get("loop_count", 0) + 1,
    }


# ─── Node 2: Searcher ─────────────────────────────────────

async def searcher_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Intent → Raw Discovery
    Reads:  search_queries
    Writes: raw_search_results
    """
    research_id = state["research_id"]
    search_queries = state["search_queries"]

    logger.info(
        "searcher node started",
        extra={"research_id": research_id, "query_count": len(search_queries)}
    )

    tavily = _get_tavily()
    all_results = []

    for query in search_queries:
        try:
            results = tavily.search(
                query=query,
                max_results=settings.max_search_results,
                search_depth="advanced",
            )
            all_results.extend(results.get("results", []))
        except Exception as e:
            logger.warning(
                "search query failed",
                extra={"research_id": research_id, "query": query, "error": str(e)}
            )
            continue

    logger.info(
        "searcher node completed",
        extra={"research_id": research_id, "results_found": len(all_results)}
    )

    return {"raw_search_results": all_results}


# ─── Node 3: Reader ───────────────────────────────────────

async def reader_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Data → Signal
    Reads:  raw_search_results
    Writes: scraped_sources
    """
    research_id = state["research_id"]
    raw_results = state["raw_search_results"]

    logger.info(
        "reader node started",
        extra={"research_id": research_id, "raw_count": len(raw_results)}
    )

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for result in raw_results:
        url = result.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(result)

    # Score and filter
    scored = sorted(
        unique_results,
        key=lambda x: x.get("score", 0.0),
        reverse=True
    )
    top_results = scored[:settings.max_search_results]

    scraped_sources: list[ScrapedSource] = []
    for result in top_results:
        content = result.get("content", "").strip()
        if not content:
            continue

        source: ScrapedSource = {
            "url": result.get("url", ""),
            "domain": _extract_domain(result.get("url", "")),
            "content": content[:1500],  # truncate to prevent token overflow
            "relevance_score": float(result.get("score", 0.0)),
        }
        scraped_sources.append(source)

    logger.info(
        "reader node completed",
        extra={"research_id": research_id, "sources_extracted": len(scraped_sources)}
    )

    return {"scraped_sources": scraped_sources}


# ─── Node 4: Writer ───────────────────────────────────────

async def writer_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Signal → Draft Knowledge
    Reads:  query, scraped_sources, output_format, critique (on loop)
    Writes: draft_text, cited_urls
    """
    research_id = state["research_id"]
    query = state["query"]
    scraped_sources = state["scraped_sources"]
    critique = state.get("critique")

    logger.info("writer node started", extra={"research_id": research_id})

    sources_text = "\n\n".join([
        f"Source [{i+1}]: {s['url']}\nDomain: {s['domain']}\n{s['content']}"
        for i, s in enumerate(scraped_sources)
    ])

    critique_context = ""
    if critique and state.get("loop_count", 0) > 1:
        critique_context = f"""
Previous draft critique:
{critique['critique_notes']}

Address these issues in your revised draft.
"""

    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=WRITER_PROMPT),
        HumanMessage(content=f"""
Research Query: {query}
Output Format: {state['output_format']}
{critique_context}

Sources:
{sources_text}

Respond in JSON with this exact structure:
{{
    "draft_text": "# Title\\n\\n## Executive Summary\\n\\n...\\n\\n## Key Findings\\n\\n- finding1\\n- finding2\\n\\n## References\\n\\n1. url1\\n2. url2",
    "cited_urls": ["url1", "url2"]
}}
""")
    ])

    try:
        content = _parse_json_response(response.content)
        draft_text = content["draft_text"]
        cited_urls = content["cited_urls"]
    except (json.JSONDecodeError, KeyError):
        logger.warning(
            "writer returned malformed JSON",
            extra={"research_id": research_id}
        )
        draft_text = response.content
        cited_urls = [s["url"] for s in scraped_sources[:3]]

    logger.info(
        "writer node completed",
        extra={"research_id": research_id, "cited_count": len(cited_urls)}
    )

    return {"draft_text": draft_text, "cited_urls": cited_urls}


# ─── Node 5: Critic ───────────────────────────────────────

async def critic_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Draft → Evaluated Delta
    Reads:  query, draft_text, cited_urls
    Writes: critique
    """
    research_id = state["research_id"]
    query = state["query"]
    draft_text = state["draft_text"]
    cited_urls = state["cited_urls"]

    logger.info("critic node started", extra={"research_id": research_id})

    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=f"""
Original Query: {query}
Cited URLs: {json.dumps(cited_urls)}

Draft Report:
{draft_text[:2000]}

Evaluate and respond in JSON:
{{
    "quality_score": 0.0,
    "completion_reason": "PASS",
    "critique_notes": "specific actionable feedback"
}}
""")
    ])

    try:
        content = _parse_json_response(response.content)
        critique: CritiqueResult = {
            "quality_score": float(content["quality_score"]),
            "completion_reason": content["completion_reason"],
            "critique_notes": content["critique_notes"],
        }
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning(
            "critic returned malformed JSON, defaulting to pass",
            extra={"research_id": research_id}
        )
        critique: CritiqueResult = {
            "quality_score": 0.85,
            "completion_reason": "PASS",
            "critique_notes": "Unable to evaluate, defaulting to pass.",
        }

    logger.info(
        "critic node completed",
        extra={
            "research_id": research_id,
            "quality_score": critique["quality_score"],
            "completion_reason": critique["completion_reason"],
        }
    )

    return {"critique": critique}


# ─── Node 6: Finalizer ────────────────────────────────────

async def finalizer_node(state: ResearchGraphState) -> dict:
    """
    Transformation: Graph State → Domain Deliverable
    Promotes draft_text → final_report
    Promotes cited_urls → final_cited_urls
    """
    research_id = state["research_id"]

    logger.info("finalizer node started", extra={"research_id": research_id})

    final_report = state["draft_text"]
    final_cited_urls = state["cited_urls"]

    logger.info(
        "research finalized",
        extra={"research_id": research_id, "cited_count": len(final_cited_urls)}
    )

    return {
        "final_report": final_report,
        "final_cited_urls": final_cited_urls,
    }