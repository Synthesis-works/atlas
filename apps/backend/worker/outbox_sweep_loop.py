"""
Eager outbox sweep loop for local development (no Redis broker required).

Celery ``beat`` normally schedules the ``outbox-sweep`` task (see
``apps/backend/worker/celery_app.py``). Running a real worker+beat requires a
broker (Redis), which is not running in the one-click local environment.

This process polls the outbox table by invoking the exact same celery task
(``apps.backend.worker.tasks.outbox_sweep_task``) every
``settings.outbox_poll_interval`` seconds. With ``CELERY_TASK_ALWAYS_EAGER=true``
every downstream celery task (evaluation, snapshot generation) executes inline
in this process, so the full post-processing pipeline runs without a broker.

Usage:
    python -m apps.backend.worker.outbox_sweep_loop
"""

import os
import sys
import threading
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "packages", "database"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from apps.backend.config import settings  # noqa: E402
from apps.backend.worker.tasks import outbox_sweep_task  # noqa: E402

# True while a sweep (and therefore any eager execution dispatched by it) is
# running in this process. The Render HTTP entrypoint uses this to keep the
# instance awake while there is actual work.
sweep_active = threading.Event()

# Stale-attempt reaper runs at most once per REAPER_INTERVAL_SECONDS sweeps.
REAPER_INTERVAL_SECONDS = 900  # 15 minutes
_last_reap_ts = [0.0]


def _maybe_reap_stale_attempts() -> None:
    """Rate-limited stale attempt reaping; never blocks the sweep on failure."""
    import time as _time

    now = _time.time()
    if now - _last_reap_ts[0] < REAPER_INTERVAL_SECONDS:
        return
    _last_reap_ts[0] = now
    try:
        from atlas_db.core.session import SessionLocal
        from apps.backend.worker.stale_attempt_reaper import reap_stale_attempts

        with SessionLocal() as db:
            reap_stale_attempts(db)
    except Exception:
        import traceback

        traceback.print_exc()


def run_sweep_once() -> None:
    sweep_active.set()
    try:
        _maybe_reap_stale_attempts()
        outbox_sweep_task()
    except Exception:
        import traceback

        traceback.print_exc()
    finally:
        sweep_active.clear()


def main() -> None:
    interval = max(int(settings.outbox_poll_interval), 1)
    print(f"[outbox-sweep-loop] starting; poll interval = {interval}s")
    print(f"[outbox-sweep-loop] CELERY_TASK_ALWAYS_EAGER = {settings.celery_task_always_eager}")
    while True:
        run_sweep_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()
