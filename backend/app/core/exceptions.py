from uuid import UUID


class AutoResearchError(Exception):
    """Base exception for all application errors."""
    pass


class ResearchNotFoundError(AutoResearchError):
    def __init__(self, research_id: UUID):
        self.research_id = research_id
        super().__init__(f"Research {research_id} not found")


class ResearchAlreadyExistsError(AutoResearchError):
    def __init__(self, research_id: UUID):
        self.research_id = research_id
        super().__init__(f"Research {research_id} already exists")


class SearchFailedError(AutoResearchError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Search failed: {reason}")


class LLMUnavailableError(AutoResearchError):
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"LLM provider unavailable: {provider}")


class ResearchTimeoutError(AutoResearchError):
    def __init__(self, research_id: UUID):
        self.research_id = research_id
        super().__init__(f"Research {research_id} timed out")


class ValidationError(AutoResearchError):
    def __init__(self, message: str):
        super().__init__(f"Validation error: {message}")