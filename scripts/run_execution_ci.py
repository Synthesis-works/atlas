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

import sys
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

    with SessionLocal() as db:
        summary = reap_stale_attempts(db)
        logger.info("startup reaper", **summary)

        executor_type = get_executor_for_environment()
        logger.info(
            "CI execution starting",
            execution_id=str(execution_id),
            executor_type=executor_type,
            correlation_id=correlation_id,
        )
        worker = ExecutionWorker(db, executor_type=executor_type)
        worker.process(execution_id, correlation_id=correlation_id)

    logger.info("CI execution finished", execution_id=str(execution_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
