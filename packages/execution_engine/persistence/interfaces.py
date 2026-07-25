import abc
import uuid

from packages.execution_engine.domain.models import Execution


class ExecutionRepository(abc.ABC):
    @abc.abstractmethod
    def save(self, execution: Execution) -> None:
        """Saves or updates an Execution aggregate and all its child entities."""
        pass

    @abc.abstractmethod
    def get(self, execution_id: uuid.UUID) -> Execution | None:
        """Retrieves an Execution aggregate by ID without locking."""
        pass

    @abc.abstractmethod
    def get_for_update(self, execution_id: uuid.UUID) -> Execution | None:
        """Retrieves an Execution aggregate by ID, applying a pessimistic lock."""
        pass

    @abc.abstractmethod
    def find_schedulable(self, limit: int = 1) -> list[Execution]:
        """Finds QUEUED executions that are ready to be scheduled, applying SKIP LOCKED."""
        pass

    @abc.abstractmethod
    def find_expired_active_attempts(self, limit: int = 50) -> list[Execution]:
        """Finds executions with expired leases on their active attempt, applying SKIP LOCKED."""
        pass
