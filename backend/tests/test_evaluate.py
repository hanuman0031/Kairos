"""Tests for ``POST /api/v1/evaluate``.

All LLM interactions are mocked so the tests run without GCP credentials.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.main import app
from app.schemas import EvaluationRequest, LLMEvaluationOutput
from app.services.llm_engine import GeminiLLMEngine, LLMServiceError

# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_PAYLOAD: dict[str, Any] = {
    "student_id": "stu-001",
    "question_id": "q-42",
    "question_text": "What is the powerhouse of the cell?",
    "student_answer": "The mitochondria",
    "subject": "biology",
    "difficulty_level": 2,
}

HAPPY_LLM_OUTPUT = LLMEvaluationOutput(
    is_correct=True,
    gap_concept="",
    hint="Great job!",
)


@pytest.fixture()
def _mock_engine_happy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch app.state.llm_engine with a mock that returns a valid evaluation."""
    mock_engine = AsyncMock(spec=GeminiLLMEngine)
    mock_engine.evaluate = AsyncMock(return_value=HAPPY_LLM_OUTPUT)
    app.state.llm_engine = mock_engine


@pytest.fixture()
def _mock_engine_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch app.state.llm_engine with a mock that raises LLMServiceError."""
    mock_engine = AsyncMock(spec=GeminiLLMEngine)
    mock_engine.evaluate = AsyncMock(
        side_effect=LLMServiceError(
            request_id="test-req",
            error_code="LLM_EXHAUSTED_RETRIES",
            original=TimeoutError("upstream timeout"),
        ),
    )
    app.state.llm_engine = mock_engine


@pytest.fixture()
def _mock_engine_bad_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch app.state.llm_engine with a mock that raises ValidationError."""
    mock_engine = AsyncMock(spec=GeminiLLMEngine)
    # Build a genuine Pydantic ValidationError
    try:
        LLMEvaluationOutput.model_validate({"is_correct": "not_a_bool", "gap_concept": "", "hint": ""})
    except ValidationError as exc:
        validation_exc = exc
    mock_engine.evaluate = AsyncMock(side_effect=validation_exc)
    app.state.llm_engine = mock_engine


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_engine_happy")
async def test_evaluate_happy_path() -> None:
    """A well-formed request should return 200 with a valid EvaluationResponse."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post("/api/v1/evaluate", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == "stu-001"
    assert data["question_id"] == "q-42"
    assert data["evaluation"]["is_correct"] is True
    assert "request_id" in data
    assert "latency_ms" in data
    assert "model_used" in data


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_engine_timeout")
async def test_evaluate_llm_timeout_returns_503() -> None:
    """When the LLM is unreachable the endpoint must return 503."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post("/api/v1/evaluate", json=VALID_PAYLOAD)

    assert resp.status_code == 503
    data = resp.json()
    assert data["error_code"] == "LLM_EXHAUSTED_RETRIES"
    assert "request_id" in data


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_engine_bad_schema")
async def test_evaluate_bad_llm_schema_returns_502() -> None:
    """When the LLM returns data that fails validation the endpoint must return 502."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.post("/api/v1/evaluate", json=VALID_PAYLOAD)

    assert resp.status_code == 502
    data = resp.json()
    assert data["error_code"] == "LLM_SCHEMA_VIOLATION"
    assert "request_id" in data


@pytest.mark.asyncio
async def test_healthz() -> None:
    """Liveness probe should always return 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.get("/healthz")

    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readyz_when_engine_set() -> None:
    """Readiness probe should report ready when the engine is present."""
    app.state.llm_engine = AsyncMock(spec=GeminiLLMEngine)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        resp = await client.get("/readyz")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
