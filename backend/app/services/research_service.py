from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.schemas.research import (
    ResearchRequest,
    ResearchCreatedResponse,
    ResearchDetailResponse,
)
from app.schemas.status import ResearchStatus, FailureReason
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── In-Memory Repository (temporary) ────────────────────
# Replace only these functions when adding a real database.
# ResearchService stays untouched.

_research_store: dict[UUID, ResearchDetailResponse] = {}


# ─── Repository Boundary ─────────────────────────────────

def _save(research: ResearchDetailResponse) -> None:
    _research_store[research.research_id] = research


def _get(research_id: UUID) -> ResearchDetailResponse | None:
    return _research_store.get(research_id)


def _update_status(
    research_id: UUID,
    status: ResearchStatus,
    failure_reason: FailureReason | None = None,
    error_message: str | None = None,
) -> ResearchDetailResponse | None:
    research = _get(research_id)
    if not research:
        return None

    updated = research.model_copy(update={
        "status": status,
        "updated_at": datetime.now(timezone.utc),
        "failure_reason": failure_reason,
        "error_message": error_message,
    })
    _save(updated)
    return updated


# ─── Service ──────────────────────────────────────────────

class ResearchService:
    """
    Owns the lifecycle of a research task.
    Knows nothing about HTTP, FastAPI, or JSON.
    Transport-agnostic by design.
    """

    def create_research(
        self, request: ResearchRequest
    ) -> ResearchCreatedResponse:
        research_id = uuid4()
        now = datetime.now(timezone.utc)

        research = ResearchDetailResponse(
            research_id=research_id,
            query=request.query,
            status=ResearchStatus.QUEUED,
            config=request.config,
            output_format=request.output_format,
            language=request.language,
            created_at=now,
            updated_at=now,
        )

        _save(research)

        logger.info(
            "research created",
            extra={"research_id": str(research_id)}
        )

        return ResearchCreatedResponse(
            research_id=research_id,
            status=ResearchStatus.QUEUED,
        )

    def get_research(
        self, research_id: UUID
    ) -> ResearchDetailResponse | None:
        research = _get(research_id)

        if not research:
            logger.warning(
                "research not found",
                extra={"research_id": str(research_id)}
            )
            return None

        logger.info(
            "research retrieved",
            extra={"research_id": str(research_id)}
        )
        return research

    def update_status(
        self,
        research_id: UUID,
        status: ResearchStatus,
        failure_reason: FailureReason | None = None,
        error_message: str | None = None,
    ) -> ResearchDetailResponse | None:
        logger.info(
            "status updated",
            extra={
                "research_id": str(research_id),
                "status": status.value
            }
        )
        return _update_status(
            research_id=research_id,
            status=status,
            failure_reason=failure_reason,
            error_message=error_message,
        )

    def list_research(self) -> list[ResearchDetailResponse]:
        logger.info("listing all research tasks")
        return list(_research_store.values())