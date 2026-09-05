"""POST /api/v1/evaluate — async student-answer evaluation endpoint.

Accepts an ``EvaluationRequest``, forwards it to the Gemini LLM engine,
and returns a validated ``EvaluationResponse``.  All errors are caught and
mapped to the uniform ``ErrorResponse`` envelope.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.schemas import (
    ErrorResponse,
    EvaluationRequest,
    EvaluationResponse,
)
from app.services.llm_engine import GeminiLLMEngine, LLMServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["evaluate"])


# ── Dependency helpers ────────────────────────────────────────────────────────


def _get_llm_engine(request: Request) -> GeminiLLMEngine:
    """Retrieve the LLM engine singleton stored on ``app.state`` during lifespan."""
    engine: GeminiLLMEngine | None = getattr(request.app.state, "llm_engine", None)
    if engine is None:
        raise RuntimeError("LLM engine not initialised — application is not ready")
    return engine


# ── Route ─────────────────────────────────────────────────────────────────────


@router.post(
    "/evaluate",
    response_model=EvaluationResponse,
    responses={
        502: {"model": ErrorResponse, "description": "LLM returned invalid schema"},
        503: {"model": ErrorResponse, "description": "LLM service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def evaluate_answer(
    body: EvaluationRequest,
    engine: GeminiLLMEngine = Depends(_get_llm_engine),
    settings: Settings = Depends(get_settings),
) -> EvaluationResponse | JSONResponse:
    """Evaluate a student answer via the Gemini LLM and return micro-feedback."""

    request_id: str = str(uuid.uuid4())
    t0 = time.perf_counter()

    try:
        evaluation = await engine.evaluate(body, request_id)
        latency_ms = (time.perf_counter() - t0) * 1_000

        return EvaluationResponse(
            request_id=request_id,
            student_id=body.student_id,
            question_id=body.question_id,
            evaluation=evaluation,
            model_used=settings.GEMINI_MODEL,
            latency_ms=round(latency_ms, 2),
        )

    except LLMServiceError as exc:
        latency_ms = (time.perf_counter() - t0) * 1_000
        logger.error(
            "LLM service error",
            extra={"request_id": request_id, "error_code": exc.error_code, "latency_ms": round(latency_ms, 2)},
        )
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                request_id=request_id,
                error_code=exc.error_code,
                message=str(exc),
            ).model_dump(mode="json"),
        )

    except ValidationError as exc:
        latency_ms = (time.perf_counter() - t0) * 1_000
        logger.error(
            "LLM schema violation",
            extra={"request_id": request_id, "latency_ms": round(latency_ms, 2), "errors": exc.error_count()},
        )
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(
                request_id=request_id,
                error_code="LLM_SCHEMA_VIOLATION",
                message=f"LLM returned data that failed schema validation: {exc.error_count()} error(s)",
            ).model_dump(mode="json"),
        )

    except Exception as exc:  # noqa: BLE001
        latency_ms = (time.perf_counter() - t0) * 1_000
        logger.exception(
            "Unexpected error during evaluation",
            extra={"request_id": request_id, "latency_ms": round(latency_ms, 2)},
        )
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please try again later.",
            ).model_dump(mode="json"),
        )


__all__: list[str] = ["router"]
