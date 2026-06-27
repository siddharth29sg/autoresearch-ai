from app.agents.langgraph.state import ResearchGraphState
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Completion Reasons ───────────────────────────────────

class CompletionReason:
    PASS = "PASS"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    CITATION_MISSING = "CITATION_MISSING"
    TIMEOUT = "TIMEOUT"


# ─── Route Targets ────────────────────────────────────────

class Route:
    REPLAN = "replan"
    WRITE_FINAL = "write_final"


# ─── Transition Policy ────────────────────────────────────

def route_after_critique(state: ResearchGraphState) -> str:
    """
    The only place in the entire codebase that decides
    whether to loop or finalize.

    Policy lives here, not in nodes.
    Thresholds live in config, not here.

    Graph owns transitions.
    Nodes own transformations.
    Config owns policy values.
    """
    settings = get_settings()
    critique = state["critique"]
    loop_count = state["loop_count"]
    research_id = state["research_id"]

    quality_score = critique["quality_score"]
    completion_reason = critique["completion_reason"]

    logger.info(
        "routing after critique",
        extra={
            "research_id": research_id,
            "quality_score": quality_score,
            "completion_reason": completion_reason,
            "loop_count": loop_count,
        }
    )

    # ─── Safety Brake (Graph Engine owns this) ────────────
    # Critic cannot override this — loop_count is never
    # touched by any reasoning node
    if loop_count >= settings.max_loop_iterations:
        logger.warning(
            "max iterations reached, forcing completion",
            extra={
                "research_id": research_id,
                "loop_count": loop_count,
            }
        )
        return Route.WRITE_FINAL

    # ─── Clean Pass ───────────────────────────────────────
    if completion_reason == CompletionReason.PASS:
        logger.info(
            "quality passed, finalizing",
            extra={"research_id": research_id}
        )
        return Route.WRITE_FINAL

    # ─── Quality Below Threshold ──────────────────────────
    if quality_score < settings.quality_threshold:
        logger.info(
            "quality below threshold, looping",
            extra={
                "research_id": research_id,
                "quality_score": quality_score,
                "threshold": settings.quality_threshold,
            }
        )
        return Route.REPLAN

    # ─── Semantic Failures → Loop ─────────────────────────
    if completion_reason in (
        CompletionReason.NEEDS_MORE_EVIDENCE,
        CompletionReason.CITATION_MISSING,
    ):
        logger.info(
            "semantic failure, looping",
            extra={
                "research_id": research_id,
                "completion_reason": completion_reason,
            }
        )
        return Route.REPLAN

    # ─── Low Confidence → Finalize anyway ────────────────
    # We don't loop on low confidence — more evidence
    # rarely fixes fundamental uncertainty in source material
    if completion_reason == CompletionReason.LOW_CONFIDENCE:
        logger.warning(
            "low confidence but finalizing",
            extra={"research_id": research_id}
        )
        return Route.WRITE_FINAL

    # ─── Default → Finalize ───────────────────────────────
    return Route.WRITE_FINAL