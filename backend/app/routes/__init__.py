"""Kairos API route modules."""

from __future__ import annotations

from app.routes.evaluate import router as evaluate_router

__all__: list[str] = ["evaluate_router"]
