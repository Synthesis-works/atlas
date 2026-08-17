import uuid
from datetime import datetime
from typing import Any

from atlas_db.models.authoring import BenchmarkVersion
from atlas_db.models.execution import Execution, ExecutionStatus
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.backend.schemas.executions import ExecutionCreate


class ExecutionService:
    @staticmethod
    def create_execution(
        db: Session,
        project_id: uuid.UUID,
        execution_in: ExecutionCreate,
        submitted_by_id: uuid.UUID,
    ) -> Execution:
        """
        Create a new execution in DRAFT or QUEUED state.
        Ensures the execution points to an immutable BenchmarkVersion.
        """
        # Fetch BenchmarkVersion to validate it exists and snapshot hash
        benchmark_version = (
            db.query(BenchmarkVersion)
            .filter(BenchmarkVersion.id == execution_in.benchmark_version_id)
            .first()
        )

        if not benchmark_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="BenchmarkVersion not found"
            )

        # Basic snapshot of what is being tested
        benchmark_hash = str(benchmark_version.id)  # In a real system, might hash config+datasets

        execution = Execution(
            project_id=project_id,
            benchmark_version_id=execution_in.benchmark_version_id,
            submitted_by_id=submitted_by_id,
            status=ExecutionStatus.QUEUED,
            target_model=execution_in.target_model,
            execution_config=execution_in.execution_config,
            benchmark_hash=benchmark_hash,
            queued_at=datetime.utcnow(),
        )

        db.add(execution)
        try:
            db.commit()
            db.refresh(execution)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create execution due to database constraint",
            )

        try:
            from apps.backend.worker.tasks import run_execution_task

            run_execution_task.delay(str(execution.id))
        except Exception:
            pass

        return execution

    @staticmethod
    def _is_terminal(state: ExecutionStatus) -> bool:
        return state in {
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.TIMED_OUT,
        }

    @staticmethod
    def update_status(db: Session, execution: Execution, new_status: ExecutionStatus) -> Execution:
        """
        Transitions the execution to a new status based on state machine rules.
        """
        current = execution.status

        if ExecutionService._is_terminal(current):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Execution is in terminal state '{current}' and cannot be transitioned to '{new_status}'.",
            )

        # Allowed transitions from QUEUED
        if current == ExecutionStatus.QUEUED:
            allowed = {
                ExecutionStatus.RUNNING,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.FAILED,
                ExecutionStatus.TIMED_OUT,
            }
            if new_status not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot transition from QUEUED to {new_status}",
                )

        # Allowed transitions from RUNNING
        elif current == ExecutionStatus.RUNNING:
            allowed = {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
                ExecutionStatus.TIMED_OUT,
            }
            if new_status not in allowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot transition from RUNNING to {new_status}",
                )

        execution.status = new_status

        # Set timestamps
        if new_status == ExecutionStatus.RUNNING and not execution.started_at:
            execution.started_at = datetime.utcnow()
        elif ExecutionService._is_terminal(new_status) and not execution.completed_at:
            execution.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(execution)
        return execution

    @staticmethod
    def cancel_execution(db: Session, execution: Execution) -> Execution:
        """
        Handles cooperative cancellation request.
        """
        if ExecutionService._is_terminal(execution.status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Execution is in terminal state '{execution.status}' and cannot be cancelled.",
            )

        execution.cancellation_requested = True

        db.commit()
        db.refresh(execution)
        return execution

    @staticmethod
    def get_execution(db: Session, execution_id: uuid.UUID) -> Execution | None:
        return db.query(Execution).filter(Execution.id == execution_id).first()

    @staticmethod
    def list_executions_for_project(
        db: Session, project_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Execution]:
        return list(
            db.query(Execution)
            .filter(Execution.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


class ExecutionApplicationService:
    def __init__(
        self,
        execution_repo: Any,
    ):
        self.execution_repo = execution_repo

    def get_recent_executions(self, limit: int = 10):
        from apps.backend.schemas.executions import ExecutionHistoryRead
        from atlas_db.models.authoring import BenchmarkVersion, Benchmark

        executions, _ = self.execution_repo.get_executions_paginated(
            limit=limit,
            offset=0,
            sort_field="created_at",
            sort_order="desc",
        )

        if not executions:
            return []

        benchmark_version_ids = [exec.benchmark_version_id for exec in executions]

        # Fetch benchmark names in one query
        query = (
            self.execution_repo.db.query(BenchmarkVersion.id, Benchmark.name)
            .join(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
            .filter(BenchmarkVersion.id.in_(benchmark_version_ids))
        )
        version_id_to_name = {row.id: row.name for row in query.all()}

        results = []
        for exec in executions:
            duration = None
            if exec.started_at and exec.completed_at:
                duration = int((exec.completed_at - exec.started_at).total_seconds() * 1000)

            benchmark_name = version_id_to_name.get(exec.benchmark_version_id, "Unknown")

            results.append(
                ExecutionHistoryRead(
                    id=exec.id,
                    benchmark_name=benchmark_name,
                    target_model=exec.target_model,
                    status=exec.status,
                    started_at=exec.started_at,
                    completed_at=exec.completed_at,
                    duration=duration,
                    project_id=exec.project_id,
                )
            )
        return results

    def get_recent_models(self, limit: int = 10):
        from apps.backend.schemas.executions import ModelActivityRead

        models_data = self.execution_repo.get_recent_models(limit=limit)

        results = []
        for target_model, last_executed_at, execution_count in models_data:
            results.append(
                ModelActivityRead(
                    name=target_model,
                    last_executed_at=last_executed_at,
                    execution_count=execution_count,
                )
            )
        return results
