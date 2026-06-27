from uuid import UUID
from datetime import datetime, timezone

from app.agents.base import BaseResearchAgent
from app.agents.langgraph.graph import research_graph
from app.schemas.research import ResearchRequest, ResearchResult
from app.schemas.status import ResearchStatus, FailureReason
from app.core.logging import get_logger
from app.core.exceptions import (
    SearchFailedError,
    LLMUnavailableError,
    ResearchTimeoutError,
)

logger = get_logger(__name__)


class LangGraphResearchAgent:
    """
    Concrete implementation of BaseResearchAgent protocol.

    This is the only file that knows LangGraph exists.

    ResearchService → BaseResearchAgent (Protocol)
                              ↓
                    LangGraphResearchAgent (this file)
                              ↓
                      research_graph (LangGraph)

    If we switch to CrewAI tomorrow:
    1. Create CrewAIResearchAgent implementing same protocol
    2. Inject it into ResearchService
    3. Delete this file
    4. Nothing else changes
    """

    async def run(
        self,
        request: ResearchRequest,
        research_id: UUID,
    ) -> ResearchResult:
        """
        Execute the full research lifecycle.

        Initializes graph state from domain request,
        runs the compiled graph,
        promotes graph output to domain ResearchResult.
        """
        research_id_str = str(research_id)
        started_at = datetime.now(timezone.utc)

        logger.info(
            "agent run started",
            extra={"research_id": research_id_str}
        )

        # ─── Initialize Graph State ───────────────────────
        # Only immutable fields are set here.
        # All other fields are populated by nodes.
        initial_state = {
            "research_id": research_id_str,
            "query": request.query,
            "output_format": request.output_format.value,
            "search_plan": "",
            "search_queries": [],
            "raw_search_results": [],
            "scraped_sources": [],
            "draft_text": "",
            "cited_urls": [],
            "critique": {
                "quality_score": 0.0,
                "completion_reason": "",
                "critique_notes": "",
            },
            "loop_count": 0,
            "final_report": "",
            "final_cited_urls": [],
        }

        try:
            # ─── Execute Graph ────────────────────────────
            final_state = await research_graph.ainvoke(initial_state)

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "agent run failed",
                extra={
                    "research_id": research_id_str,
                    "error": error_msg,
                }
            )
            # Classify the error into domain exceptions
            if "tavily" in error_msg.lower() or "search" in error_msg.lower():
                raise SearchFailedError(reason=error_msg)
            if "groq" in error_msg.lower() or "llm" in error_msg.lower():
                raise LLMUnavailableError(provider="groq")
            if "timeout" in error_msg.lower():
                raise ResearchTimeoutError(research_id=research_id)
            # Re-raise as generic domain error
            raise SearchFailedError(reason=f"Unexpected error: {error_msg}")

        # ─── Promote Graph State → Domain Result ──────────
        # This is the only place graph state crosses a boundary.
        # Everything else in the graph is internal.
        finished_at = datetime.now(timezone.utc)
        time_taken = (finished_at - started_at).total_seconds()

        result = ResearchResult(
            report=final_state["final_report"],
            sources_used=final_state["final_cited_urls"],
            key_findings=_extract_key_findings(final_state["final_report"]),
            follow_up_questions=[],   # future: add a follow-up node
            tokens_used=0,            # future: accumulate from node responses
            time_taken_seconds=time_taken,
        )

        logger.info(
            "agent run completed",
            extra={
                "research_id": research_id_str,
                "time_taken_seconds": time_taken,
                "sources_used": len(result.sources_used),
            }
        )

        return result

    async def cancel(self, research_id: UUID) -> None:
        """
        Cancel an in-progress research task.

        LangGraph doesn't natively support cancellation yet.
        We log the intent — full cancellation support
        will be implemented with background task management.
        """
        logger.warning(
            "cancel requested",
            extra={"research_id": str(research_id)}
        )


# ─── Helpers ──────────────────────────────────────────────

def _extract_key_findings(report: str) -> list[str]:
    """
    Extracts bullet points or numbered items from report
    as key findings for the summary view.

    Simple heuristic for V1 — can be replaced with
    an LLM extraction node later.
    """
    findings = []
    for line in report.split("\n"):
        line = line.strip()
        if line.startswith(("- ", "* ", "• ")):
            findings.append(line[2:].strip())
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".):":
            findings.append(line[2:].strip())

    return findings[:10]   # cap at 10 key findings