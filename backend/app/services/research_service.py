from uuid import UUID, uuid4
from datetime import datetime, timezone
from app.schemas.research import (
    ResearchRequest,
    ResearchCreatedResponse,
    ResearchDetailResponse,
)
from app.schemas.status import ResearchStatus, FailureReason
from app.core.logging import get_logger
from app.core.exceptions import AutoResearchError
from app.agents.base import BaseResearchAgent

logger = get_logger(__name__)

_research_store: dict[UUID, ResearchDetailResponse] = {}


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


class ResearchService:
    """
    Owns the lifecycle of a research task.
    Knows nothing about HTTP, FastAPI, or JSON.
    Knows nothing about LangGraph.
    Transport-agnostic and framework-agnostic by design.
    """

    def __init__(self, agent: BaseResearchAgent):
        self.agent = agent

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

    async def run_research(self, research_id: UUID) -> None:
        _update_status(research_id, ResearchStatus.PLANNING)

        try:
            research = _get(research_id)
            if not research:
                return

            request = ResearchRequest(
                query=research.query,
                config=research.config,
                output_format=research.output_format,
                language=research.language,
            )

            _update_status(research_id, ResearchStatus.SEARCHING)
            result = await self.agent.run(request, research_id)

            updated = research.model_copy(update={
                "status": ResearchStatus.COMPLETED,
                "result": result,
                "updated_at": datetime.now(timezone.utc),
            })
            _save(updated)

            logger.info(
                "research completed",
                extra={"research_id": str(research_id)}
            )

        except AutoResearchError as e:
            logger.error(
                "research failed",
                extra={
                    "research_id": str(research_id),
                    "error": str(e),
                }
            )
            _update_status(
                research_id,
                ResearchStatus.FAILED,
                error_message=str(e),
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
                "status": status.value,
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

    def delete_research(self, research_id: UUID) -> None:
        if research_id in _research_store:
            del _research_store[research_id]
            logger.info(
                "research deleted",
                extra={"research_id": str(research_id)}
            )