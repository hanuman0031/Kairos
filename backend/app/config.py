"""Application configuration via pydantic-settings with environment variable support."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralised, validated application settings.

    Every field can be overridden by the corresponding environment variable
    (case-insensitive).  No ``env_prefix`` is applied so variable names match
    the field names exactly.
    """

    # ── Google Cloud / Vertex AI ──────────────────────────────────────────
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ── LLM retry / timeout knobs ─────────────────────────────────────────
    LLM_MAX_RETRIES: int = 3
    LLM_BASE_DELAY_S: float = 0.5
    LLM_TIMEOUT_S: float = 8.0

    # ── API-level timeout ─────────────────────────────────────────────────
    API_REQUEST_TIMEOUT_S: float = 10.0

    # ── Observability ─────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"

    model_config = {
        "env_prefix": "",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """Factory cached at module level so ``Depends(get_settings)`` is fast."""
    return _settings


_settings = Settings()

__all__: list[str] = ["Settings", "get_settings"]
