from functools import lru_cache
from fastapi import Depends
from app.agents.langgraph_agent import LangGraphResearchAgent
from app.agents.base import BaseResearchAgent
from app.services.research_service import ResearchService


@lru_cache
def get_agent() -> BaseResearchAgent:
    """
    Returns the concrete agent implementation.
    Swap this function to change the agent framework.
    Routes never know which agent is underneath.
    """
    return LangGraphResearchAgent()


def get_research_service(
    agent: BaseResearchAgent = Depends(get_agent),
) -> ResearchService:
    """
    Constructs ResearchService with all dependencies injected.
    If ResearchService gains new dependencies tomorrow,
    only this function changes — routes stay untouched.
    """
    return ResearchService(agent=agent)