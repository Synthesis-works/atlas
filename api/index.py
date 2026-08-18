"""
Vercel Python runtime entrypoint shim.

Vercel detects FastAPI framework applications from a supported entrypoint and
bundles the whole app into a single Vercel Function. This module re-exports the
ASGI application instance defined in apps/backend/main.py so the monorepo
imports resolve inside the function bundle (see vercel.json for the function
configuration).

Local development is unaffected: the backend is still started with
`uvicorn apps.backend.main:app`.
"""

from apps.backend.main import app

__all__ = ["app"]
