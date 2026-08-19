"""
Fire-and-forget wake client used by the API to nudge the Render worker.

The wake request must never fail execution submission and must never block the
API request, so it runs on a daemon thread with a short timeout and swallows
every error. Callers must only invoke ``notify_worker_wake()`` AFTER the outbox
transaction has been committed; a wake sent before the commit could be observed
by a worker that polls the outbox faster than the API commits.

``notify_login_warmup()`` is a best-effort warm-up sent after a successful
login. It never blocks or fails the login response and is throttled per API
instance so a burst of logins does not produce a burst of wake requests.
"""

import logging
import threading
import time
import urllib.request

from apps.backend.config import settings

logger = logging.getLogger(__name__)

WAKE_TIMEOUT_SECONDS = 5.0

# Minimum interval between login warm-up wakes (per API instance). /wake is
# idempotent, so duplicate wakes across serverless instances are harmless.
WARMUP_COOLDOWN_SECONDS = 300

_warmup_lock = threading.Lock()
# -inf so the first warm-up is never throttled: monotonic() can be arbitrarily
# small on freshly booted machines (CI runners, cold Vercel instances).
_last_warmup_sent: float = float("-inf")


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


def notify_login_warmup() -> None:
    """
    Best-effort worker warm-up after a successful login.

    Fire-and-forget and throttled to one wake per ``WARMUP_COOLDOWN_SECONDS``
    per API instance. Never raises and never blocks the login response. This is
    an optimization only: execution submission still sends its own wake, which
    remains the authoritative mechanism for correctness.
    """
    if not settings.worker_wake_url:
        return
    global _last_warmup_sent
    with _warmup_lock:
        now = time.monotonic()
        if now - _last_warmup_sent < WARMUP_COOLDOWN_SECONDS:
            return
        _last_warmup_sent = now
    threading.Thread(target=_send_wake, daemon=True, name="worker-warmup").start()
