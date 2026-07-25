import uuid
from datetime import datetime

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
        return (
            db.query(Execution)
            .filter(Execution.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
