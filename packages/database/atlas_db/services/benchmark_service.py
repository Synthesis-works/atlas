import uuid

from atlas_db.events import DomainEvent
from atlas_db.models.authoring import (
    Benchmark,
    BenchmarkState,
    BenchmarkVersion,
)
from atlas_db.repositories.authoring import (
    BenchmarkLifecycleRepository,
    BenchmarkRepository,
    BenchmarkVersionRepository,
)


class BenchmarkServiceError(Exception):
    """Base exception for BenchmarkService."""


class PermissionDeniedError(BenchmarkServiceError):
    """Raised when user does not have permission."""


class InvalidStateTransitionError(BenchmarkServiceError):
    """Raised when an invalid state transition is attempted."""


class InvariantViolationError(BenchmarkServiceError):
    """Raised when validation rules are not met."""


class ImmutableVersionError(BenchmarkServiceError):
    """Raised when attempting to modify a published or archived benchmark version."""


class ConcurrencyViolationError(BenchmarkServiceError):
    """Raised when concurrent modification is detected."""


class BenchmarkService:
    """Service layer for Benchmark Authoring (Phase A)."""

    def __init__(
        self,
        benchmark_repo: BenchmarkRepository,
        lifecycle_repo: BenchmarkLifecycleRepository,
        version_repo: BenchmarkVersionRepository,
    ):
        self.benchmark_repo = benchmark_repo
        self.lifecycle_repo = lifecycle_repo
        self.version_repo = version_repo

    def create_benchmark(
        self,
        project_id: uuid.UUID,
        author_id: uuid.UUID,
        name: str,
        objective: str | None = None,
        difficulty: str | None = None,
        domain: str | None = None,
        type: str | None = None,
        visibility: str | None = None,
    ) -> tuple[Benchmark, list[DomainEvent]]:
        """Create a new benchmark in PROPOSAL state."""
        benchmark_data = {
            "project_id": project_id,
            "author_id": author_id,
            "name": name,
            "objective": objective,
            "difficulty": difficulty,
            "domain": domain,
            "type": type,
            "visibility": visibility,
            "status": BenchmarkState.PROPOSAL,
        }

        try:
            benchmark = self.benchmark_repo.create(obj_in=benchmark_data, commit=False)

            lifecycle_data = {
                "benchmark_id": benchmark.id,
                "state": BenchmarkState.PROPOSAL,
                "changed_by_id": author_id,
            }
            self.lifecycle_repo.create(obj_in=lifecycle_data, commit=False)

            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(benchmark)

            from atlas_db.events import BenchmarkCreatedEvent

            event = BenchmarkCreatedEvent(
                aggregate_id=benchmark.id, actor_id=author_id, name=name, project_id=project_id
            )
            return benchmark, [event]
        except Exception:
            self.benchmark_repo.db.rollback()
            raise

    def can_edit(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can edit."""
        if user_role in ["org_admin", "project_write", "project_admin"]:
            return True
        if benchmark.author_id == user_id:
            return True
        return False

    def can_publish(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can publish."""
        if user_role in ["org_admin", "project_admin"]:
            return True
        if benchmark.author_id == user_id:
            return True
        return False

    def can_archive(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can archive."""
        if user_role == "org_admin":
            return True
        if benchmark.author_id == user_id:
            return True
        return False

    def create_version(
        self,
        benchmark_id: uuid.UUID,
        version_string: str,
        user_id: uuid.UUID,
        user_role: str,
        dataset_version_ids: list[uuid.UUID] | None = None,
        evaluation_strategy_id: uuid.UUID | None = None,
    ) -> tuple[BenchmarkVersion, list[DomainEvent]]:
        """Create a new version for a benchmark."""
        try:
            benchmark = self.benchmark_repo.get_for_update(benchmark_id)
            if not benchmark:
                raise ValueError("Benchmark not found")

            # Check if an active editable version already exists
            if benchmark.status in [
                BenchmarkState.DESIGN,
                BenchmarkState.DRAFT,
                BenchmarkState.VALIDATION,
                BenchmarkState.REVIEW,
            ]:
                raise ConcurrencyViolationError("An active editable version already exists.")

            if benchmark.status == BenchmarkState.ARCHIVE:
                raise InvalidStateTransitionError(
                    "Cannot create a version for an archived benchmark."
                )

            # Validate permission
            if not self.can_edit(benchmark, user_id, user_role):
                raise PermissionDeniedError("User does not have permission to create versions.")

            version_data = {
                "benchmark_id": benchmark.id,
                "version_string": version_string,
                "created_by_id": user_id,
                "evaluation_strategy_id": evaluation_strategy_id,
            }
            version = self.version_repo.create(obj_in=version_data, commit=False)

            if dataset_version_ids:
                from atlas_db.models.dataset import DatasetVersion

                dataset_versions = (
                    self.version_repo.db
                    .query(DatasetVersion)
                    .filter(DatasetVersion.id.in_(dataset_version_ids))
                    .all()
                )
                if len(dataset_versions) != len(dataset_version_ids):
                    raise ValueError("One or more dataset versions not found.")
                version.dataset_versions = dataset_versions

            # Change benchmark state to DRAFT
            benchmark = self.benchmark_repo.update(
                db_obj=benchmark, obj_in={"status": BenchmarkState.DRAFT}, commit=False
            )

            lifecycle_data = {
                "benchmark_id": benchmark.id,
                "state": BenchmarkState.DRAFT,
                "changed_by_id": user_id,
            }
            self.lifecycle_repo.create(obj_in=lifecycle_data, commit=False)

            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(version)

            from atlas_db.events import BenchmarkVersionCreatedEvent

            event = BenchmarkVersionCreatedEvent(
                aggregate_id=version.id,
                actor_id=user_id,
                benchmark_id=benchmark_id,
                version_string=version_string,
                dataset_version_ids=dataset_version_ids,
                evaluation_strategy_id=evaluation_strategy_id,
            )
            return version, [event]
        except Exception:
            self.benchmark_repo.db.rollback()
            raise

    def update_version(
        self,
        version_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        dataset_version_ids: list[uuid.UUID] | None = None,
        evaluation_strategy_id: uuid.UUID | None = None,
    ) -> tuple[BenchmarkVersion, list[DomainEvent]]:
        """Update an existing version."""
        try:
            version = self.version_repo.get_for_update(version_id)
            if not version:
                raise ValueError("Version not found")

            benchmark = self.benchmark_repo.get(version.benchmark_id)

            if not self.can_edit(benchmark, user_id, user_role):
                raise PermissionDeniedError("User does not have permission to edit versions.")

            self.assert_editable(benchmark)

            update_data = {}
            if evaluation_strategy_id is not None:
                update_data["evaluation_strategy_id"] = evaluation_strategy_id

            updated_version = self.version_repo.update(
                db_obj=version, obj_in=update_data, commit=False
            )

            if dataset_version_ids is not None:
                from atlas_db.models.dataset import DatasetVersion

                dataset_versions = (
                    self.version_repo.db
                    .query(DatasetVersion)
                    .filter(DatasetVersion.id.in_(dataset_version_ids))
                    .all()
                )
                if len(dataset_versions) != len(dataset_version_ids):
                    raise ValueError("One or more dataset versions not found.")
                updated_version.dataset_versions = dataset_versions

            self.version_repo.db.commit()
            self.version_repo.db.refresh(updated_version)

            from atlas_db.events import BenchmarkVersionUpdatedEvent

            event = BenchmarkVersionUpdatedEvent(
                aggregate_id=version_id,
                actor_id=user_id,
                dataset_version_ids=dataset_version_ids,
                evaluation_strategy_id=evaluation_strategy_id,
            )
            return updated_version, [event]
        except Exception:
            self.version_repo.db.rollback()
            raise

    def transition_state(
        self,
        benchmark_id: uuid.UUID,
        target_state: BenchmarkState,
        user_id: uuid.UUID,
        user_role: str,
    ) -> tuple[Benchmark, list[DomainEvent]]:
        """Transition benchmark state following the lifecycle engine rules with locking."""

        try:
            # Pessimistic lock on the benchmark for state transitions
            benchmark = self.benchmark_repo.get_for_update(benchmark_id)
            if not benchmark:
                raise ValueError("Benchmark not found")

            current_state = BenchmarkState(benchmark.status)

            # Validate permissions
            if target_state == BenchmarkState.PUBLISHED:
                if not self.can_publish(benchmark, user_id, user_role):
                    raise PermissionDeniedError(
                        "User does not have permission to publish this benchmark."
                    )
            elif target_state == BenchmarkState.ARCHIVE:
                if not self.can_archive(benchmark, user_id, user_role):
                    raise PermissionDeniedError(
                        "User does not have permission to archive this benchmark."
                    )
            else:
                if not self.can_edit(benchmark, user_id, user_role):
                    raise PermissionDeniedError(
                        "User does not have permission to edit this benchmark."
                    )

            # Check allowed transitions
            allowed_transitions = {
                BenchmarkState.PROPOSAL: [BenchmarkState.DESIGN, BenchmarkState.ARCHIVE],
                BenchmarkState.DESIGN: [BenchmarkState.DRAFT, BenchmarkState.ARCHIVE],
                BenchmarkState.DRAFT: [
                    BenchmarkState.VALIDATION,
                    BenchmarkState.DESIGN,
                    BenchmarkState.ARCHIVE,
                ],
                BenchmarkState.VALIDATION: [BenchmarkState.REVIEW, BenchmarkState.DRAFT],
                BenchmarkState.REVIEW: [BenchmarkState.PUBLISHED, BenchmarkState.DRAFT],
                BenchmarkState.PUBLISHED: [BenchmarkState.ARCHIVE],
                BenchmarkState.ARCHIVE: [],
            }

            if target_state not in allowed_transitions.get(current_state, []):
                raise InvalidStateTransitionError(
                    f"Cannot transition from {current_state} to {target_state}"
                )

            # Invariants for specific states
            if target_state in [
                BenchmarkState.VALIDATION,
                BenchmarkState.REVIEW,
                BenchmarkState.PUBLISHED,
            ]:
                self._validate_invariants(benchmark)

            updated_benchmark = self.benchmark_repo.update(
                db_obj=benchmark, obj_in={"status": target_state}, commit=False
            )

            lifecycle_data = {
                "benchmark_id": benchmark.id,
                "state": target_state,
                "changed_by_id": user_id,
            }
            self.lifecycle_repo.create(obj_in=lifecycle_data, commit=False)

            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(updated_benchmark)

            from atlas_db.events import BenchmarkLifecycleTransitionEvent

            event = BenchmarkLifecycleTransitionEvent(
                aggregate_id=benchmark_id,
                actor_id=user_id,
                from_state=str(current_state.value),
                to_state=str(target_state.value),
            )
            return updated_benchmark, [event]
        except Exception:
            self.benchmark_repo.db.rollback()
            raise

    def validate_version(
        self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str
    ) -> tuple[BenchmarkVersion, list[DomainEvent]]:
        try:
            version = self.version_repo.get(version_id)
            if not version:
                raise ValueError("Version not found")

            benchmark = self.benchmark_repo.get(version.benchmark_id)

            # Perform semantic validation
            if not benchmark.categories:
                raise InvariantViolationError(
                    "Benchmark must have at least one category to be validated."
                )
            if not benchmark.capabilities:
                raise InvariantViolationError(
                    "Benchmark must have at least one capability to be validated."
                )
            if not version.dataset_versions:
                raise InvariantViolationError(
                    "Benchmark version must have at least one dataset bound to be validated."
                )
            if not version.evaluation_strategy_id:
                raise InvariantViolationError(
                    "Benchmark version must have an evaluation strategy to be validated."
                )

            # Transition state to VALIDATION
            benchmark, events = self.transition_state(
                benchmark.id, BenchmarkState.VALIDATION, user_id, user_role
            )
            return version, events
        except Exception:
            raise

    def publish_version(
        self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str
    ) -> tuple[BenchmarkVersion, list[DomainEvent]]:
        try:
            version = self.version_repo.get(version_id)
            if not version:
                raise ValueError("Version not found")

            # Transition state from REVIEW to PUBLISHED
            benchmark, events = self.transition_state(
                version.benchmark_id, BenchmarkState.PUBLISHED, user_id, user_role
            )
            return version, events
        except Exception:
            raise

    def archive_version(
        self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str
    ) -> tuple[BenchmarkVersion, list[DomainEvent]]:
        try:
            version = self.version_repo.get(version_id)
            if not version:
                raise ValueError("Version not found")

            # Transition state from PUBLISHED to ARCHIVE
            benchmark, events = self.transition_state(
                version.benchmark_id, BenchmarkState.ARCHIVE, user_id, user_role
            )
            return version, events
        except Exception:
            raise

    def _validate_invariants(self, benchmark: Benchmark):
        """Validate invariant rules required for validation, review, and published states."""
        if not benchmark.categories:
            raise InvariantViolationError("Benchmark must have at least one Category assigned.")
        if not benchmark.capabilities:
            raise InvariantViolationError("Benchmark must have at least one Capability assigned.")

        active_version = None
        if benchmark.versions:
            active_version = benchmark.versions[-1]

        if not active_version:
            raise InvariantViolationError("Benchmark must have an active version for validation.")

        if not getattr(active_version, "dataset_bindings", None) and not hasattr(
            active_version, "_has_datasets"
        ):
            raise InvariantViolationError("At least one valid dataset version must be linked.")

        if not getattr(active_version, "evaluation_strategies", None) and not hasattr(
            active_version, "_has_evaluators"
        ):
            raise InvariantViolationError("At least one evaluation strategy must be configured.")

        if not getattr(active_version, "metrics", None) and not hasattr(
            active_version, "_has_metrics"
        ):
            raise InvariantViolationError("At least one scoring metric must be defined.")

    def assert_editable(self, benchmark: Benchmark):
        """Ensure benchmark is not in an immutable state."""
        if benchmark.status in [BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE]:
            raise ImmutableVersionError(f"Cannot edit benchmark in {benchmark.status} state.")
