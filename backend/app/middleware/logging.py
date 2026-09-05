"""JSON structured-logging ASGI middleware for every HTTP request.

Emits one JSON-lines log entry per request containing: request_id, method,
path, status_code, latency_ms, timestamp, and user_agent.  The root logger
is also configured to emit JSON-lines output.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger.json import JsonFormatter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("kairos.access")


def setup_json_logging(log_level: str = "INFO") -> None:
    """Configure the root logger to output JSON-lines via *python-json-logger*.

    Should be called exactly once during application startup (lifespan).
    """
    handler = logging.StreamHandler()
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Remove any previously-attached handlers to avoid duplicates during tests
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level.upper())


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that logs structured JSON for every request."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id: str = request.headers.get("x-request-id", str(uuid.uuid4()))
        # Attach to request state so downstream handlers can reference it
        request.state.request_id = request_id

        t0 = time.perf_counter()
        response: Response = await call_next(request)
        latency_ms = (time.perf_counter() - t0) * 1_000

        log_data: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_agent": request.headers.get("user-agent", ""),
        }

        logger.info("request completed", extra=log_data)

        # Echo the request_id back in the response for traceability
        response.headers["x-request-id"] = request_id
        return response


__all__: list[str] = ["StructuredLoggingMiddleware", "setup_json_logging"]
