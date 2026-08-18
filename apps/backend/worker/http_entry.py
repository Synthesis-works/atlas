"""
Render HTTP entrypoint for the Atlas worker.

Runs the existing outbox sweep loop (``apps.backend.worker.outbox_sweep_loop``)
in a background thread and exposes a minimal HTTP surface so Render Free can
host and health-check the process:

    GET  /health  -> liveness probe (public, used by Render health checks)
    POST /wake    -> trigger an immediate outbox sweep; requires
                     ``WORKER_AUTH_TOKEN`` bearer authentication. The API uses
                     this to wake a sleeping worker after a job is committed.

While a sweep is in progress the process pings its own public URL
(``WORKER_PUBLIC_URL``) every ``RENDER_KEEPALIVE_INTERVAL_SECONDS`` seconds.
Render Free spins an instance down after 15 minutes of no inbound traffic, so
this self-ping keeps the instance awake for the duration of a long run and
stops as soon as there is no work, letting the instance sleep again.

Usage:
    python -m apps.backend.worker.http_entry
"""

import os
import sys
import threading
import time
import urllib.request

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "database"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from fastapi import FastAPI, Header, HTTPException  # noqa: E402
import uvicorn  # noqa: E402

from apps.backend.config import settings  # noqa: E402
from apps.backend.worker import outbox_sweep_loop  # noqa: E402

KEEPALIVE_TIMEOUT_SECONDS = 10.0

app = FastAPI(title="Atlas Worker", version="1.0.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "atlas-worker",
        "celery_task_always_eager": settings.celery_task_always_eager,
    }


def _authorize(authorization: str | None) -> None:
    expected = settings.worker_auth_token
    if not expected:
        raise HTTPException(status_code=401, detail="Worker authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if authorization.removeprefix("Bearer ").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid bearer token")


@app.post("/wake")
def wake(authorization: str | None = Header(default=None)) -> dict[str, str]:
    """Trigger an immediate outbox sweep. Returns without waiting for it."""
    _authorize(authorization)
    threading.Thread(
        target=outbox_sweep_loop.run_sweep_once, daemon=True, name="wake-sweep"
    ).start()
    return {"status": "waking"}


def _self_ping() -> None:
    url = settings.worker_public_url
    if not url:
        return
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=KEEPALIVE_TIMEOUT_SECONDS) as response:
            response.read()
    except Exception:
        pass


def _keepalive_loop() -> None:
    interval = max(int(settings.render_keepalive_interval_seconds), 1)
    while True:
        time.sleep(interval)
        if outbox_sweep_loop.sweep_active.is_set():
            _self_ping()


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("BIND_HOST", "0.0.0.0")

    sweep_thread = threading.Thread(
        target=outbox_sweep_loop.main, daemon=True, name="outbox-sweep-loop"
    )
    sweep_thread.start()

    keepalive_thread = threading.Thread(
        target=_keepalive_loop, daemon=True, name="render-keepalive"
    )
    keepalive_thread.start()

    print(f"[http-entry] Atlas worker HTTP server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())


if __name__ == "__main__":
    main()
