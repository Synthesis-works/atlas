import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from packages.execution_engine.domain.clock import Clock
from packages.execution_engine.domain.events import DomainEvent
from packages.execution_engine.domain.exceptions import InvariantViolationError


class ExecutionState(Enum):
    QUEUED = "QUEUED"
    SCHEDULED = "SCHEDULED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"


class AttemptStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    CANCELLED = "CANCELLED"


class ArtifactType(Enum):
    LOGS = "LOGS"
    MODEL_OUTPUT = "MODEL_OUTPUT"
    EVALUATION_RESULT = "EVALUATION_RESULT"


@dataclass
class Artifact:
    id: uuid.UUID
    attempt_id: uuid.UUID
    type: ArtifactType
    storage_uri: str


@dataclass
class Lease:
    id: uuid.UUID
    attempt_id: uuid.UUID
    worker_id: uuid.UUID
    acquired_at: datetime
    expires_at: datetime


@dataclass
class ExecutionAttempt:
    id: uuid.UUID
    execution_id: uuid.UUID
    attempt_number: int
    status: AttemptStatus = AttemptStatus.IN_PROGRESS
    started_at: datetime = field(default_factory=Clock.now)
    finished_at: datetime | None = None
    error_message: str | None = None
    lease: Lease | None = None
    _artifacts: list[Artifact] = field(default_factory=list)

    @property
    def artifacts(self) -> tuple[Artifact, ...]:
        return tuple(self._artifacts)

    def add_artifact(self, artifact: Artifact):
        self._artifacts.append(artifact)


@dataclass
class Execution:
    id: uuid.UUID
    benchmark_version_id: uuid.UUID
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: ExecutionState = ExecutionState.QUEUED
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=Clock.now)
    updated_at: datetime = field(default_factory=Clock.now)
    _attempts: list[ExecutionAttempt] = field(default_factory=list)
    _events: list[DomainEvent] = field(default_factory=list)
    max_retries: int = 3

    @classmethod
    def rehydrate(
        cls,
        id: uuid.UUID,
        benchmark_version_id: uuid.UUID,
        project_id: uuid.UUID,
        status: ExecutionState,
        created_by: uuid.UUID,
        created_at: datetime,
        updated_at: datetime,
        max_retries: int,
        attempts: list[ExecutionAttempt],
    ) -> "Execution":
        """Reconstructs the aggregate from persistence without triggering domain invariants."""
        instance = cls(
            id=id,
            benchmark_version_id=benchmark_version_id,
            project_id=project_id,
            status=status,
            created_by=created_by,
            created_at=created_at,
            updated_at=updated_at,
            max_retries=max_retries,
        )
        instance._attempts = attempts
        # Pending events are purely transient and should not be persisted or rehydrated.
        instance._events = []
        return instance

    @property
    def attempts(self) -> tuple[ExecutionAttempt, ...]:
        return tuple(self._attempts)

    def begin_attempt(
        self, worker_id: uuid.UUID, clock: Clock, lease_duration_seconds: int = 300
    ) -> ExecutionAttempt:
        if any(a.status == AttemptStatus.IN_PROGRESS for a in self._attempts):
            raise InvariantViolationError(
                "Exactly one execution attempt is permitted to be in progress."
            )

        attempt_number = len(self._attempts) + 1
        now = clock.now()

        attempt = ExecutionAttempt(
            id=uuid.uuid4(),
            execution_id=self.id,
            attempt_number=attempt_number,
            status=AttemptStatus.IN_PROGRESS,
            started_at=now,
        )

        lease = Lease(
            id=uuid.uuid4(),
            attempt_id=attempt.id,
            worker_id=worker_id,
            acquired_at=now,
            expires_at=now + timedelta(seconds=lease_duration_seconds),
        )
        attempt.lease = lease
        self._attempts.append(attempt)
        return attempt

    def finish_attempt(self, clock: Clock):
        attempt = self.current_attempt
        if attempt and attempt.status == AttemptStatus.IN_PROGRESS:
            attempt.status = AttemptStatus.SUCCESS
            attempt.finished_at = clock.now()

    def fail_attempt(self, error_message: str, clock: Clock):
        attempt = self.current_attempt
        if attempt and attempt.status == AttemptStatus.IN_PROGRESS:
            attempt.status = AttemptStatus.FAILED
            attempt.finished_at = clock.now()
            attempt.error_message = error_message

    def cancel_attempt(self, clock: Clock):
        attempt = self.current_attempt
        if attempt and attempt.status == AttemptStatus.IN_PROGRESS:
            attempt.status = AttemptStatus.CANCELLED
            attempt.finished_at = clock.now()

    @property
    def current_attempt(self) -> ExecutionAttempt | None:
        if not self._attempts:
            return None
        return self._attempts[-1]

    def is_terminal(self) -> bool:
        return self.status in {
            ExecutionState.COMPLETED,
            ExecutionState.FAILED,
            ExecutionState.CANCELLED,
        }

    def has_active_lease(self, clock: Clock) -> bool:
        attempt = self.current_attempt
        if not attempt or not attempt.lease or attempt.status != AttemptStatus.IN_PROGRESS:
            return False
        return attempt.lease.expires_at > clock.now()

    def record_event(self, event: DomainEvent):
        self._events.append(event)

    def pull_events(self) -> tuple[DomainEvent, ...]:
        """Returns all unpulled events and clears the internal queue."""
        events = tuple(self._events)
        self._events.clear()
        return events
