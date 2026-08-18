"""
Fire-and-forget wake client used by the API to nudge the Render worker.

The wake request must never fail execution submission and must never block the
API request, so it runs on a daemon thread with a short timeout and swallows
every error. Callers must only invoke ``notify_worker_wake()`` AFTER the outbox
transaction has been committed; a wake sent before the commit could be observed
by a worker that polls the outbox faster than the API commits.
"""

import logging
import threading
import urllib.request

from apps.backend.config import settings

logger = logging.getLogger(__name__)

WAKE_TIMEOUT_SECONDS = 5.0


def _send_wake() -> None:
    url = settings.worker_wake_url
    if not url:
        return
    headers: dict[str, str] = {}
    token = settings.worker_auth_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        request = urllib.request.Request(url, data=b"", method="POST", headers=headers)
        with urllib.request.urlopen(request, timeout=WAKE_TIMEOUT_SECONDS) as response:
            response.read()
        logger.info("Worker wake request sent", extra={"worker_wake_url": url})
    except Exception:
        logger.warning("Worker wake request failed; execution submission is unaffected")


def notify_worker_wake() -> None:
    """Schedule a non-blocking wake nudge. Never raises; never blocks."""
    if not settings.worker_wake_url:
        return
    threading.Thread(target=_send_wake, daemon=True, name="worker-wake").start()
