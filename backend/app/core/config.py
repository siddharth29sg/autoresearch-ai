from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.core.enums import Environment, LLMProvider, ModelTier
from app.schemas.status import OutputFormat


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── App ──────────────────────────────────────────────
    app_name: str = "autoresearch-ai"
    app_version: str = "0.1.0"
    app_env: Environment = Environment.DEVELOPMENT
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    # ─── API ──────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # ─── LLM ──────────────────────────────────────────────
    groq_api_key: str
    default_llm_provider: LLMProvider = LLMProvider.GROQ
    default_model_tier: ModelTier = ModelTier.STANDARD
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)

    # ─── Search ───────────────────────────────────────────
    tavily_api_key: str
    max_search_results: int = Field(default=10, ge=1, le=100)
    search_timeout_seconds: int = Field(default=30, ge=1)

    # ─── Research ─────────────────────────────────────────
    max_research_timeout: int = Field(default=300, ge=1)
    max_concurrent_researches: int = Field(default=10, ge=1)
    default_output_format: OutputFormat = OutputFormat.MARKDOWN

    # ─── Database (future) ────────────────────────────────
    database_url: str = Field(default="sqlite:///./autoresearch.db")

    # ─── Research Quality ─────────────────────────────────────
    quality_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    max_loop_iterations: int = Field(default=3, ge=1, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()