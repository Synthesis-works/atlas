"""CI execution-plane driver.

Runs a single benchmark execution inside a GitHub Actions runner using the
same production code path as the Celery worker:

    reap stale attempts -> ExecutionWorker.process(execution_id)

Invoked by .github/workflows/benchmark-execute.yml:

    python scripts/run_execution_ci.py <execution_id> [correlation_id]

Required environment (provided as Actions secrets):
    DATABASE_URL, ENVIRONMENT=production, ATLAS_BENCHMARK_IMAGE,
    ATLAS_BENCHMARK_NETWORK, provider API keys (allow-listed downstream).

NOTE: This driver is intentionally inert until the repository variable
BENCHMARK_EXECUTION_ENABLED is set to "true" AND the GitHub Actions
execution-plane decision is approved (ToS / public-log review).
"""

from __future__ import annotations

import os
import sys
import time
import uuid

REPO_ROOT = __file__.rsplit("\\scripts", 1)[0].rsplit("/scripts", 1)[0]
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, REPO_ROOT + "/packages/database")

import structlog  # noqa: E402

from atlas_db.core.session import SessionLocal  # noqa: E402
from apps.backend.worker.execution_worker import ExecutionWorker  # noqa: E402
from apps.backend.worker.executor_init import get_executor_for_environment, init_executors  # noqa: E402
from apps.backend.worker.stale_attempt_reaper import reap_stale_attempts  # noqa: E402

logger = structlog.get_logger(__name__)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_execution_ci.py <execution_id> [correlation_id]", file=sys.stderr)
        return 2

    try:
        execution_id = uuid.UUID(sys.argv[1])
    except ValueError:
        print(f"invalid execution id: {sys.argv[1]!r}", file=sys.stderr)
        return 2

    correlation_id = sys.argv[2] if len(sys.argv) > 2 else f"gh-run-{execution_id}"

    init_executors()

    t_start = time.perf_counter()
    with SessionLocal() as db:
        summary = reap_stale_attempts(db)
        logger.info("startup reaper", **summary)

        executor_type = get_executor_for_environment()
        logger.info(
            "CI execution starting",
            execution_id=str(execution_id),
            executor_type=executor_type,
            correlation_id=correlation_id,
            gh_run_id=os.environ.get("GH_RUN_ID", ""),
            runner=os.environ.get("RUNNER_LABEL", ""),
        )
        worker = ExecutionWorker(db, executor_type=executor_type)
        worker.process(execution_id, correlation_id=correlation_id)

    total_ms = int((time.perf_counter() - t_start) * 1000)
    _record_backend_metrics(execution_id, total_ms)

    logger.info(
        "CI execution finished",
        execution_id=str(execution_id),
        total_ms=total_ms,
    )
    return 0


def _record_backend_metrics(execution_id: uuid.UUID, total_ms: int) -> None:
    """Persist backend observability metrics onto the latest attempt.

    Best-effort: metrics enrichment must never fail the execution.
    Records: GH run id/url, runner label, image build/execute timings, and
    total wall-clock time so an Atlas execution id traces to its GitHub
    Actions run and Docker container.
    """
    import os

    from sqlalchemy import select

    from atlas_db.models.execution import ExecutionAttempt

    gh_run_id = os.environ.get("GH_RUN_ID", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_url = f"https://github.com/{repo}/actions/runs/{gh_run_id}" if gh_run_id else ""
    metrics = {
        "backend": "github_actions",
        "gh_run_id": gh_run_id,
        "gh_run_url": run_url,
        "runner": os.environ.get("RUNNER_LABEL", ""),
        "driver_total_ms": total_ms,
    }
    for key in ("IMAGE_BUILD_MS", "EXECUTE_MS"):
        val = os.environ.get(key)
        if val and val.isdigit():
            metrics[key.lower()] = int(val)

    try:
        with SessionLocal() as db:
            attempt = (
                db.execute(
                    select(ExecutionAttempt)
                    .where(ExecutionAttempt.execution_id == execution_id)
                    .order_by(ExecutionAttempt.attempt_number.desc())
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if attempt is not None:
                merged = {**(attempt.metrics or {}), **metrics}
                attempt.metrics = merged
                db.commit()
    except Exception as exc:  # noqa: BLE001 - best-effort only
        logger.warning("metrics persistence failed", error=str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
