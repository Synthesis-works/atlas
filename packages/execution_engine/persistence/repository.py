import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timezone

from packages.execution_engine.domain.models import Execution, ExecutionState

from packages.execution_engine.persistence.interfaces import ExecutionRepository
from packages.execution_engine.persistence.models import ExecutionModel, ExecutionAttemptModel, LeaseModel
from packages.execution_engine.persistence.mapper import ExecutionMapper

class SqlAlchemyExecutionRepository(ExecutionRepository):
    def __init__(self, session: Session):
        self.session = session

    def save(self, execution: Execution) -> None:
        """Saves or updates an Execution aggregate."""
        model = self.session.get(ExecutionModel, execution.id)
        if model is None:
            model = ExecutionMapper.to_model(execution)
            self.session.add(model)
        else:
            ExecutionMapper.update_model(execution, model)
        self.session.flush()

    def get(self, execution_id: uuid.UUID) -> Optional[Execution]:
        """Retrieves an Execution aggregate by ID without locking."""
        model = self.session.get(ExecutionModel, execution_id)
        if model is None:
            return None
        return ExecutionMapper.to_domain(model)

    def get_for_update(self, execution_id: uuid.UUID) -> Optional[Execution]:
        """Retrieves an Execution aggregate by ID, applying a pessimistic lock."""
        # Using with_for_update() for pessimistic row locking
        stmt = (
            select(ExecutionModel)
            .where(ExecutionModel.id == execution_id)
            .with_for_update()
        )
        model = self.session.execute(stmt).scalar_one_or_none()
        if model is None:
            return None
        return ExecutionMapper.to_domain(model)

    def find_schedulable(self, limit: int = 1) -> List[Execution]:
        """Finds QUEUED executions that are ready to be scheduled, applying SKIP LOCKED."""
        stmt = (
            select(ExecutionModel)
            .where(ExecutionModel.status == ExecutionState.QUEUED)
            .order_by(ExecutionModel.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        models = self.session.execute(stmt).scalars().all()
        return [ExecutionMapper.to_domain(m) for m in models]

    def find_expired_active_attempts(self, limit: int = 50) -> List[Execution]:
        """Finds executions with expired leases on their active attempt, applying SKIP LOCKED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(ExecutionModel)
            .join(ExecutionAttemptModel)
            .join(LeaseModel)
            .where(ExecutionModel.status.in_([ExecutionState.STARTING, ExecutionState.RUNNING]))
            .where(LeaseModel.expires_at < now)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        models = self.session.execute(stmt).scalars().unique().all()
        return [ExecutionMapper.to_domain(m) for m in models]
