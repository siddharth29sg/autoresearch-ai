from typing import TypedDict, Annotated
from operator import add


class ScrapedSource(TypedDict):
    """
    Represents a single piece of evidence extracted from a source.
    Named 'Evidence' conceptually — stores distilled text, never raw HTML.
    """
    url: str
    domain: str
    content: str        # clean markdown, never raw DOM
    relevance_score: float


class CritiqueResult(TypedDict):
    """
    Structured output from the Critic node.
    Separates the score (numeric) from the intent (semantic).
    """
    quality_score: float        # 0.0 to 1.0
    completion_reason: str      # PASS | NEEDS_MORE_EVIDENCE |
                                # LOW_CONFIDENCE | CITATION_MISSING | TIMEOUT
    critique_notes: str         # specific, actionable feedback for Writer


class ResearchGraphState(TypedDict):
    """
    The single source of truth for one research execution.

    Ownership rules:
    - Immutable fields: never reassigned after Adapter initialization
    - Temporary fields: consumed and overwritten within the graph
    - Persistent fields: promoted to domain model by Adapter on completion

    Serialization note:
    All fields are plain Python types (str, float, int, list, dict).
    Safe to checkpoint. No LLM clients, no file handles, no callables.
    """

    # ─── Immutable (set by Adapter, never reassigned) ─────
    query: str
    output_format: str          # markdown | pdf | json
    research_id: str            # str not UUID — JSON serialization safe

    # ─── Planning (Temporary) ─────────────────────────────
    search_plan: str            # Planner's reasoning about the query
    search_queries: list[str]   # targeted search strings

    # ─── Searching (Temporary) ────────────────────────────
    # Annotated[list, add] tells LangGraph to APPEND not REPLACE
    # Multiple search calls accumulate results safely
    raw_search_results: Annotated[list[dict], add]

    # ─── Reading (Temporary) ──────────────────────────────
    scraped_sources: list[ScrapedSource]    # distilled evidence, never raw HTML

    # ─── Writing (Semi-persistent) ────────────────────────
    draft_text: str
    cited_urls: list[str]       # only URLs actually used in draft

    # ─── Critiquing (Temporary) ───────────────────────────
    critique: CritiqueResult

    # ─── Loop Control (Owned by Graph Engine) ─────────────
    loop_count: int             # Graph increments this, Critic never touches it

    # ─── Final Output (Persistent → promoted to domain) ───
    final_report: str           # survives graph execution
    final_cited_urls: list[str] # verified citations promoted to DB