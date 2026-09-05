"""Vertex AI / Gemini LLM wrapper with exponential backoff, jitter, and structured output.

This module encapsulates all interaction with Google's Generative AI API behind
a single ``GeminiLLMEngine`` class that is initialised once during application
lifespan and injected into route handlers via FastAPI dependency injection.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any

import google.genai as genai
from google.genai import types as genai_types
from pydantic import ValidationError

from app.config import Settings
from app.schemas import EvaluationRequest, LLMEvaluationOutput

logger = logging.getLogger(__name__)

# ── Custom exception ──────────────────────────────────────────────────────────


class LLMServiceError(Exception):
    """Raised when the LLM service is unreachable after all retry attempts."""

    def __init__(
        self,
        request_id: str,
        error_code: str,
        original: Exception | None = None,
    ) -> None:
        self.request_id = request_id
        self.error_code = error_code
        self.original = original
        super().__init__(
            f"[{request_id}] {error_code}: {original!r}" if original else f"[{request_id}] {error_code}"
        )


# ── Response schema dict for Gemini structured output ─────────────────────────

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "is_correct": {"type": "BOOLEAN"},
        "gap_concept": {"type": "STRING"},
        "hint": {"type": "STRING"},
    },
    "required": ["is_correct", "gap_concept", "hint"],
}

# ── Few-shot prompt template ─────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = """\
You are a precise, encouraging educational evaluator for the Kairos micro-feedback platform.

Given a question and a student's answer, you MUST output a JSON object with exactly three fields:
- "is_correct" (boolean): whether the student's answer is substantially correct.
- "gap_concept" (string): if the answer is incorrect or partially correct, the specific concept \
or knowledge gap the student is missing.  If the answer is correct, return an empty string "".
- "hint" (string): a short, Socratic hint that nudges the student toward the correct understanding \
without giving the answer away.  If the answer is correct, return a brief encouragement.

### Example 1 — Correct answer
Question: What is the powerhouse of the cell?
Student answer: The mitochondria is the powerhouse of the cell.
Output:
{"is_correct": true, "gap_concept": "", "hint": "Great job! You nailed it."}

### Example 2 — Incorrect answer
Question: Explain Newton's second law of motion.
Student answer: Newton's second law says that every action has an equal and opposite reaction.
Output:
{"is_correct": false, "gap_concept": "Confusion between Newton's second law (F=ma) and third law (action-reaction).", "hint": "Think about how force, mass, and acceleration relate to each other — that's the key relationship in the *second* law."}
"""


def _build_user_prompt(request: EvaluationRequest) -> str:
    """Build the user-turn prompt from the evaluation request."""
    return (
        f"Subject: {request.subject}\n"
        f"Difficulty level: {request.difficulty_level}/5\n\n"
        f"Question:\n{request.question_text}\n\n"
        f"Student answer:\n{request.student_answer}"
    )


# ── Engine ────────────────────────────────────────────────────────────────────


class GeminiLLMEngine:
    """Async wrapper around the ``google.genai`` SDK with retry logic."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model = settings.GEMINI_MODEL
        self._max_retries = settings.LLM_MAX_RETRIES
        self._base_delay = settings.LLM_BASE_DELAY_S
        self._timeout = settings.LLM_TIMEOUT_S

        self._client: genai.Client = genai.Client(
            project=settings.GCP_PROJECT_ID,
            location=settings.GCP_LOCATION,
        )

        logger.info(
            "GeminiLLMEngine initialised",
            extra={
                "model": self._model,
                "project": settings.GCP_PROJECT_ID,
                "location": settings.GCP_LOCATION,
            },
        )

    # ── Public API ────────────────────────────────────────────────────────

    async def evaluate(
        self,
        request: EvaluationRequest,
        request_id: str,
    ) -> LLMEvaluationOutput:
        """Send the evaluation request to Gemini and return validated output.

        Retries with exponential back-off + jitter on transient failures.
        """
        user_prompt = _build_user_prompt(request)
        last_exception: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            t0 = time.perf_counter()
            try:
                raw_text = await self._call_llm(user_prompt, request_id, attempt)
                latency_ms = (time.perf_counter() - t0) * 1_000

                logger.info(
                    "LLM call succeeded",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt,
                        "latency_ms": round(latency_ms, 2),
                    },
                )

                return self._parse_response(raw_text, request_id)

            except (ValidationError, json.JSONDecodeError) as exc:
                # Schema / parse errors are *not* retryable — the model returned
                # garbage and retrying is unlikely to fix it.
                logger.warning(
                    "LLM response failed validation",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt,
                        "error": str(exc),
                    },
                )
                raise

            except Exception as exc:  # noqa: BLE001 — broad catch for transient API errors
                latency_ms = (time.perf_counter() - t0) * 1_000
                last_exception = exc

                logger.warning(
                    "LLM call failed (transient)",
                    extra={
                        "request_id": request_id,
                        "attempt": attempt,
                        "latency_ms": round(latency_ms, 2),
                        "error": str(exc),
                    },
                )

                if attempt < self._max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.info(
                        "Retrying after backoff",
                        extra={
                            "request_id": request_id,
                            "next_attempt": attempt + 1,
                            "delay_s": round(delay, 3),
                        },
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise LLMServiceError(
            request_id=request_id,
            error_code="LLM_EXHAUSTED_RETRIES",
            original=last_exception,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    async def _call_llm(
        self,
        user_prompt: str,
        request_id: str,
        attempt: int,
    ) -> str:
        """Execute a single LLM call with timeout."""

        generation_config = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.2,
        )

        response = await asyncio.wait_for(
            self._generate(user_prompt, generation_config),
            timeout=self._timeout,
        )

        # Defensive: the SDK may return an empty response
        if not response or not response.text:
            raise LLMServiceError(
                request_id=request_id,
                error_code="LLM_EMPTY_RESPONSE",
            )

        return response.text

    async def _generate(
        self,
        user_prompt: str,
        config: genai_types.GenerateContentConfig,
    ) -> Any:
        """Thin wrapper so we can use ``asyncio.wait_for`` around the SDK call."""
        return await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model,
            contents=user_prompt,
            config=config,
        )

    @staticmethod
    def _parse_response(raw_text: str, request_id: str) -> LLMEvaluationOutput:
        """Validate raw JSON text against ``LLMEvaluationOutput``."""
        try:
            return LLMEvaluationOutput.model_validate_json(raw_text)
        except (ValidationError, json.JSONDecodeError):
            logger.error(
                "Failed to parse LLM JSON output",
                extra={"request_id": request_id, "raw_text": raw_text[:500]},
            )
            raise

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff with jitter: base * 2^attempt + random jitter."""
        exp = self._base_delay * (2 ** attempt)
        jitter = random.uniform(0, self._base_delay)  # noqa: S311
        return exp + jitter


__all__: list[str] = ["GeminiLLMEngine", "LLMServiceError"]
