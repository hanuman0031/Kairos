"""FastAPI application entry point — lifespan, middleware, routers, and health probes.

Start with::

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.middleware.logging import StructuredLoggingMiddleware, setup_json_logging
from app.routes import evaluate_router
from app.services.llm_engine import GeminiLLMEngine

logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise shared resources on startup; tear down on shutdown."""
    settings: Settings = get_settings()

    # 1. Wire up structured JSON logging before anything else
    setup_json_logging(settings.LOG_LEVEL)

    # 2. Create the LLM engine singleton
    engine = GeminiLLMEngine(settings)
    app.state.llm_engine = engine
    logger.info("Kairos backend started", extra={"environment": settings.ENVIRONMENT})

    yield

    # Teardown
    app.state.llm_engine = None
    logger.info("Kairos backend shutdown complete")


# ── App factory ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Kairos — EdTech Micro-Feedback API",
    version="0.1.0",
    description="Real-time student answer evaluation powered by Gemini.",
    lifespan=lifespan,
)

# ── Middleware (order matters — last added runs first) ────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production via env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(StructuredLoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(evaluate_router)


# ── Health probes ─────────────────────────────────────────────────────────────


@app.get("/healthz", tags=["health"])
async def liveness() -> dict[str, str]:
    """Kubernetes liveness probe — always returns 200 if the process is up."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/readyz", tags=["health"])
async def readiness() -> dict[str, str | bool]:
    """Kubernetes readiness probe — verifies the LLM engine is initialised."""
    engine = getattr(app.state, "llm_engine", None)
    ready = engine is not None
    return {
        "status": "ready" if ready else "not_ready",
        "llm_engine_initialised": ready,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


__all__: list[str] = ["app"]
