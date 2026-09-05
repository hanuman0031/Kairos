"""Pydantic v2 request / response schemas for the Kairos evaluation API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request ───────────────────────────────────────────────────────────────────


class EvaluationRequest(BaseModel):
    """Incoming student-answer evaluation payload."""

    student_id: str = Field(..., min_length=1, max_length=64)
    question_id: str = Field(..., min_length=1, max_length=128)
    question_text: str = Field(..., min_length=10, max_length=2000)
    student_answer: str = Field(..., min_length=1, max_length=5000)
    subject: Optional[str] = Field(default="general", min_length=1, max_length=64)
    difficulty_level: Optional[int] = Field(default=3, ge=1, le=5)

    model_config = ConfigDict(strict=True, frozen=True)


# ── LLM structured output ────────────────────────────────────────────────────


class LLMEvaluationOutput(BaseModel):
    """Schema enforced on the raw LLM JSON response."""

    is_correct: bool
    gap_concept: str = Field(..., max_length=500)
    hint: str = Field(..., max_length=1000)

    model_config = ConfigDict(strict=True, frozen=True)


# ── API response ──────────────────────────────────────────────────────────────


class EvaluationResponse(BaseModel):
    """Successful evaluation response returned to the client."""

    request_id: str
    student_id: str
    question_id: str
    evaluation: LLMEvaluationOutput
    model_used: str
    latency_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(strict=True, frozen=True)


# ── Error response ────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Uniform error envelope returned on any failure."""

    request_id: str
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(strict=True, frozen=True)


__all__: list[str] = [
    "EvaluationRequest",
    "LLMEvaluationOutput",
    "EvaluationResponse",
    "ErrorResponse",
]
