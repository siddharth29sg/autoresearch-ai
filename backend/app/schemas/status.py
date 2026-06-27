from enum import Enum


class ResearchStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    VALIDATING = "validating"
    PLANNING = "planning"
    SEARCHING = "searching"
    READING = "reading"
    SYNTHESIZING = "synthesizing"
    CRITIQUING = "critiquing"
    IMPROVING = "improving"
    WRITING = "writing"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"
    ARCHIVED = "archived"


class FailureReason(str, Enum):
    SEARCH_FAILED = "search_failed"
    LLM_UNAVAILABLE = "llm_unavailable"
    EXPORT_FAILED = "export_failed"
    TIMED_OUT = "timed_out"
    EMPTY_RESULTS = "empty_results"
    VALIDATION_FAILED = "validation_failed"
    QUOTA_EXCEEDED = "quota_exceeded"


class ResearchDepth(str, Enum):
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"


class ResearchSource(str, Enum):
    WEB = "web"
    ARXIV = "arxiv"
    PDF = "pdf"
    YOUTUBE = "youtube"