from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.status import (
    ResearchStatus,
    FailureReason,
    ResearchDepth,
    OutputFormat,
    ResearchSource,
)


# ─── Config ───────────────────────────────────────────────

class ResearchConfig(BaseModel):
    depth: ResearchDepth = ResearchDepth.STANDARD
    sources: list[ResearchSource] = Field(
        default_factory=lambda: [ResearchSource.WEB, ResearchSource.ARXIV]
    )
    max_results: int = Field(default=10, ge=1, le=100)


# ─── Request ──────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    config: ResearchConfig = Field(default_factory=ResearchConfig)
    output_format: OutputFormat = OutputFormat.MARKDOWN
    language: str = Field(default="en")
    webhook_url: Optional[str] = None


# ─── Result ───────────────────────────────────────────────

class ResearchResult(BaseModel):
    report: str
    sources_used: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    time_taken_seconds: float = 0.0


# ─── POST /research response ──────────────────────────────

class ResearchCreatedResponse(BaseModel):
    research_id: UUID
    status: ResearchStatus


# ─── GET /research list item ──────────────────────────────

class ResearchSummary(BaseModel):
    research_id: UUID
    query: str
    status: ResearchStatus
    created_at: datetime


# ─── GET /research/{id} response ─────────────────────────

class ResearchDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    research_id: UUID = Field(default_factory=uuid4)
    query: str
    status: ResearchStatus = ResearchStatus.CREATED
    config: ResearchConfig
    output_format: OutputFormat
    language: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    result: Optional[ResearchResult] = None
    failure_reason: Optional[FailureReason] = None
    error_message: Optional[str] = None