"""Verify a dry-run execution produced real container provenance and outputs.

Usage: verify_dryrun_execution.py <execution_id>

Asserts (exit non-zero on any failure):
  - Execution status is COMPLETED.
  - Latest attempt ran on the docker executor with a real container id,
    exit_code == 0, termination_reason == "completed", timed_out is false,
    and an image digest was recorded.
  - At least one ModelOutput exists with raw_output == "mocked_output".
  - No test case has duplicate ModelOutputs (M-3 invariant).
"""

from __future__ import annotations

import sys
import uuid

REPO_ROOT = __file__.rsplit("\\scripts", 1)[0].rsplit("/scripts", 1)[0]
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, REPO_ROOT + "/packages/database")

from atlas_db.core.session import SessionLocal  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_dryrun_execution.py <execution_id>", file=sys.stderr)
        return 2
    execution_id = uuid.UUID(sys.argv[1])

    from sqlalchemy import func

    from atlas_db.models.execution import (
        AttemptStatus,
        Execution,
        ExecutionAttempt,
        ExecutionStatus,
        ModelOutput,
    )

    failures: list[str] = []

    with SessionLocal() as db:
        execution = db.get(Execution, execution_id)
        if execution is None:
            print(f"FAIL: execution {execution_id} not found", file=sys.stderr)
            return 1

        if execution.status != ExecutionStatus.COMPLETED:
            failures.append(f"status={execution.status!r}, expected COMPLETED")

        attempt = (
            db.query(ExecutionAttempt)
            .filter(ExecutionAttempt.execution_id == execution_id)
            .order_by(ExecutionAttempt.attempt_number.desc())
            .first()
        )
        if attempt is None:
            failures.append("no ExecutionAttempt rows")
        else:
            checks = {
                "attempt.status": (attempt.status, AttemptStatus.COMPLETED),
                "attempt.executor_type": (attempt.executor_type, "docker"),
                "attempt.container_id set": (bool(attempt.container_id), True),
                "attempt.exit_code": (attempt.exit_code, 0),
                "attempt.termination_reason": (attempt.termination_reason, "completed"),
                "attempt.timed_out": (bool(attempt.timed_out), False),
                "attempt.image_digest set": (bool(attempt.image_digest), True),
            }
            for name, (actual, expected) in checks.items():
                if actual != expected:
                    failures.append(f"{name}={actual!r}, expected {expected!r}")

        outputs = (
            db.query(ModelOutput).filter(ModelOutput.execution_id == execution_id).all()
        )
        if not outputs:
            failures.append("no ModelOutput rows")
        for out in outputs:
            if out.raw_output != "mocked_output":
                failures.append(f"raw_output={out.raw_output!r}, expected 'mocked_output'")

        dupes = (
            db.query(
                ModelOutput.test_case_id,
                func.count(ModelOutput.id).label("n"),
            )
            .filter(ModelOutput.execution_id == execution_id)
            .group_by(ModelOutput.test_case_id)
            .having(func.count(ModelOutput.id) > 1)
            .all()
        )
        if dupes:
            failures.append(f"duplicate ModelOutputs for test cases: {[str(d[0]) for d in dupes]}")

        print(
            f"DRYRUN-VERIFY: status={execution.status} "
            f"container={getattr(attempt, 'container_id', None)} "
            f"digest={(getattr(attempt, 'image_digest', '') or '')[:20]} "
            f"outputs={len(outputs)}"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}", file=sys.stderr)
        return 1
    print("DRYRUN-VERIFY: all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
