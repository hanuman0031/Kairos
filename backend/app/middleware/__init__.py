"""Kairos middleware modules — structured logging and observability."""

from __future__ import annotations

from app.middleware.logging import StructuredLoggingMiddleware

__all__: list[str] = ["StructuredLoggingMiddleware"]
