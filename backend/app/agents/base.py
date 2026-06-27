from typing import Protocol, runtime_checkable
from uuid import UUID
from app.schemas.research import ResearchRequest, ResearchResult


@runtime_checkable
class BaseResearchAgent(Protocol):
    """
    Interface every research agent must satisfy.

    ResearchService depends only on this abstraction.
    It never imports LangGraph, CrewAI, or any framework directly.

    To add a new agent framework tomorrow:
    1. Create a new class that implements this protocol
    2. Pass it into ResearchService
    3. Nothing else changes
    """

    async def run(
        self,
        request: ResearchRequest,
        research_id: UUID,
    ) -> ResearchResult:
        """
        Execute the full research lifecycle.

        Responsible for:
        - Planning the research strategy
        - Searching and reading sources
        - Critiquing and improving output
        - Returning a structured ResearchResult

        Never raises HTTP exceptions.
        Raises domain exceptions only (defined in core/exceptions.py).
        """
        ...

    async def cancel(self, research_id: UUID) -> None:
        """
        Cancel an in-progress research task.
        Agent is responsible for cleanup.
        """
        ...