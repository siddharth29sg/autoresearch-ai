from functools import lru_cache
from fastapi import Depends
from app.agents.langgraph_agent import LangGraphResearchAgent
from app.agents.base import BaseResearchAgent
from app.services.research_service import ResearchService


@lru_cache
def get_agent() -> BaseResearchAgent:
    return LangGraphResearchAgent()


@lru_cache
def get_research_service() -> ResearchService:
    """
    Single instance shared across all requests.
    lru_cache ensures this is only constructed once.
    _research_store is shared correctly as a result.
    """
    return ResearchService(agent=get_agent())