from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.api.dependencies import get_research_service
from app.services.research_service import ResearchService
from app.schemas.research import (
    ResearchRequest,
    ResearchCreatedResponse,
    ResearchDetailResponse,
    ResearchSummary,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/research", tags=["research"])


@router.post(
    "",
    response_model=ResearchCreatedResponse,
    status_code=202,
    summary="Start a new research task",
)
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    service: ResearchService = Depends(get_research_service),
) -> ResearchCreatedResponse:
    """
    Accepts a research request and immediately returns
    a research_id and status=queued.

    Research runs asynchronously in the background.
    Poll GET /research/{id} for results.
    """
    response = service.create_research(request)

    background_tasks.add_task(
        service.run_research,
        response.research_id,
    )

    logger.info(
        "research accepted",
        extra={"research_id": str(response.research_id)}
    )

    return response


@router.get(
    "",
    response_model=list[ResearchSummary],
    summary="List all research tasks",
)
async def list_research(
    service: ResearchService = Depends(get_research_service),
) -> list[ResearchSummary]:
    """
    Returns a lightweight summary of all research tasks.
    Does not include full reports.
    """
    researches = service.list_research()
    return [
        ResearchSummary(
            research_id=r.research_id,
            query=r.query,
            status=r.status,
            created_at=r.created_at,
        )
        for r in researches
    ]


@router.get(
    "/{research_id}",
    response_model=ResearchDetailResponse,
    summary="Get full research details",
)
async def get_research(
    research_id: UUID,
    service: ResearchService = Depends(get_research_service),
) -> ResearchDetailResponse:
    """
    Returns the full research object including report
    when status=completed.
    """
    research = service.get_research(research_id)

    if not research:
        raise HTTPException(
            status_code=404,
            detail=f"Research {research_id} not found",
        )

    return research


@router.delete(
    "/{research_id}",
    status_code=204,
    summary="Delete a research task",
)
async def delete_research(
    research_id: UUID,
    service: ResearchService = Depends(get_research_service),
) -> None:
    """
    Deletes a research task.
    Returns 204 No Content on success.
    """
    research = service.get_research(research_id)

    if not research:
        raise HTTPException(
            status_code=404,
            detail=f"Research {research_id} not found",
        )

    service.delete_research(research_id)