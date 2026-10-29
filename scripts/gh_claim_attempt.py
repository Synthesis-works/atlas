"""Claim a PENDING github_actions attempt for a specific workflow run.

Called as the first DB-touching step inside the GitHub Actions execution
workflow. Atomically binds the oldest active PENDING attempt for the execution
to this run (worker_id = "gha-run:<run_id>", started_at = now). Exiting
non-zero means this run must NOT execute: either another run already claimed
the attempt, or the attempt is gone (reaped/cancelled).

Options:
  --allow-create  Create the PENDING attempt if none exists. Used ONLY by
                  manual workflow_dispatch synthetic runs; repository_dispatch
                  attempts are always pre-created by the Atlas dispatcher.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

REPO_ROOT = __file__.rsplit("\\scripts", 1)[0].rsplit("/scripts", 1)[0]
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, REPO_ROOT + "/packages/database")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--runner", default="")
    parser.add_argument("--allow-create", action="store_true")
    args = parser.parse_args()

    import uuid as uuid_module

    from sqlalchemy import select

    from atlas_db.core.session import SessionLocal
    from atlas_db.models.execution import AttemptStatus, ExecutionAttempt

    try:
        execution_id = uuid_module.UUID(args.execution_id)
    except ValueError:
        print(f"invalid execution id: {args.execution_id!r}", file=sys.stderr)
        return 2

    worker_id = f"gha-run:{args.run_id}"
    with SessionLocal() as db:
        attempt = (
            db.execute(
                select(ExecutionAttempt)
                .where(
                    ExecutionAttempt.execution_id == execution_id,
                    ExecutionAttempt.status == AttemptStatus.PENDING,
                    ExecutionAttempt.executor_type == "github_actions",
                )
                .order_by(ExecutionAttempt.attempt_number.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .first()
        )

        if attempt is None and args.allow_create:
            latest = (
                db.query(ExecutionAttempt)
                .filter(ExecutionAttempt.execution_id == execution_id)
                .order_by(ExecutionAttempt.attempt_number.desc())
                .first()
            )
            attempt = ExecutionAttempt(
                execution_id=execution_id,
                attempt_number=(latest.attempt_number + 1) if latest else 1,
                status=AttemptStatus.PENDING,
                executor_type="github_actions",
                correlation_id=f"manual-{args.run_id}",
            )
            db.add(attempt)
            db.flush()

        if attempt is None:
            print(
                f"CLAIM-FAILED: no claimable PENDING github_actions attempt for "
                f"execution {execution_id} (already claimed, reaped, or never "
                f"dispatched). Refusing to execute.",
                file=sys.stderr,
            )
            return 1

        claimed_at = datetime.now(UTC)
        attempt.worker_id = worker_id
        attempt.started_at = claimed_at
        # Transition out of PENDING so no other run can claim this attempt.
        attempt.status = AttemptStatus.CONTAINER_CREATED

        # Timing only. `started_at` is overwritten again by the worker
        # immediately before container launch, so the dispatch -> claim leg is
        # otherwise unrecoverable; `created_at` is set by the dispatcher when
        # the PENDING attempt was queued.
        timing: dict[str, object] = {"claim_at": claimed_at.isoformat()}
        created_at = attempt.created_at
        if created_at is not None:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            timing["dispatch_at"] = created_at.isoformat()
            timing["queue_wait_ms"] = max(0, int((claimed_at - created_at).total_seconds() * 1000))
        if args.runner:
            timing["runner"] = args.runner

        attempt.metrics = {**(attempt.metrics or {}), **timing}
        db.commit()
        print(f"CLAIMED attempt={attempt.id} number={attempt.attempt_number} worker_id={worker_id}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
