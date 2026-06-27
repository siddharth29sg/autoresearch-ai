from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.schemas.research import (
    ResearchRequest,
    ResearchCreatedResponse,
    ResearchDetailResponse,
    ResearchConfig,
)
from app.schemas.status import ResearchStatus, FailureReason


# ─── In-Memory Repository (temporary) ────────────────────
# This is the boundary Q5 referred to.
# When we add a database, only this dict and its access
# methods change. ResearchService stays untouched.

_research_store: dict[UUID, ResearchDetailResponse] = {}


# ─── Repository Interface ─────────────────────────────────

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

    # We use model_copy to preserve immutability of original
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
        """
        Creates a new research task.
        Generates ID immediately so we can track it
        before any background work begins.
        """
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

        return ResearchCreatedResponse(
            research_id=research_id,
            status=ResearchStatus.QUEUED,
        )

    def get_research(
        self, research_id: UUID
    ) -> ResearchDetailResponse | None:
        """
        Retrieves full research detail by ID.
        Returns None if not found — API layer decides
        whether to raise 404.
        """
        return _get(research_id)

    def update_status(
        self,
        research_id: UUID,
        status: ResearchStatus,
        failure_reason: FailureReason | None = None,
        error_message: str | None = None,
    ) -> ResearchDetailResponse | None:
        """
        Updates research status.
        Called by the agent as it moves through lifecycle.
        """
        return _update_status(
            research_id=research_id,
            status=status,
            failure_reason=failure_reason,
            error_message=error_message,
        )

    def list_research(self) -> list[ResearchDetailResponse]:
        """
        Returns all research tasks.
        Later this will be filtered by user_id.
        """
        return list(_research_store.values())