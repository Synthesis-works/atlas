import uuid
from typing import Optional, List, Dict, Any

from atlas_db.models.authoring import (
    Benchmark, 
    BenchmarkState, 
    BenchmarkLifecycle, 
    BenchmarkVersion,
)
from atlas_db.repositories.authoring import (
    BenchmarkRepository,
    BenchmarkLifecycleRepository,
    BenchmarkVersionRepository
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
        version_repo: BenchmarkVersionRepository
    ):
        self.benchmark_repo = benchmark_repo
        self.lifecycle_repo = lifecycle_repo
        self.version_repo = version_repo

    def create_benchmark(
        self, 
        project_id: uuid.UUID, 
        author_id: uuid.UUID, 
        name: str, 
        objective: Optional[str] = None,
        difficulty: Optional[str] = None,
        domain: Optional[str] = None,
        type: Optional[str] = None,
        visibility: Optional[str] = None
    ) -> Benchmark:
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
            "status": BenchmarkState.PROPOSAL
        }
        
        try:
            benchmark = self.benchmark_repo.create(obj_in=benchmark_data, commit=False)
            
            lifecycle_data = {
                "benchmark_id": benchmark.id,
                "state": BenchmarkState.PROPOSAL,
                "changed_by_id": author_id
            }
            self.lifecycle_repo.create(obj_in=lifecycle_data, commit=False)
            
            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(benchmark)
            return benchmark
        except Exception:
            self.benchmark_repo.db.rollback()
            raise

    def can_edit(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can edit unpublished versions."""
        if benchmark.status in [BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE]:
            return False
        if user_role in ["org_admin", "project_write"]:
            return True
        return False

    def can_publish(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can publish."""
        if user_role == "org_admin":
            return True
        if benchmark.author_id == user_id and user_role == "project_write":
            return True
        return False

    def can_archive(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can archive."""
        if user_role == "org_admin":
            return True
        if benchmark.author_id == user_id:
            return True
        return False

    def transition_state(
        self,
        benchmark_id: uuid.UUID,
        target_state: BenchmarkState,
        user_id: uuid.UUID,
        user_role: str
    ) -> Benchmark:
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
                    raise PermissionDeniedError("User does not have permission to publish this benchmark.")
            elif target_state == BenchmarkState.ARCHIVE:
                if not self.can_archive(benchmark, user_id, user_role):
                    raise PermissionDeniedError("User does not have permission to archive this benchmark.")
            else:
                if not self.can_edit(benchmark, user_id, user_role):
                    raise PermissionDeniedError("User does not have permission to edit this benchmark.")

            # Check allowed transitions
            allowed_transitions = {
                BenchmarkState.PROPOSAL: [BenchmarkState.DESIGN, BenchmarkState.ARCHIVE],
                BenchmarkState.DESIGN: [BenchmarkState.DRAFT, BenchmarkState.ARCHIVE],
                BenchmarkState.DRAFT: [BenchmarkState.VALIDATION, BenchmarkState.DESIGN, BenchmarkState.ARCHIVE],
                BenchmarkState.VALIDATION: [BenchmarkState.REVIEW, BenchmarkState.DRAFT],
                BenchmarkState.REVIEW: [BenchmarkState.PUBLISHED, BenchmarkState.DRAFT],
                BenchmarkState.PUBLISHED: [BenchmarkState.ARCHIVE],
                BenchmarkState.ARCHIVE: []
            }

            if target_state not in allowed_transitions.get(current_state, []):
                raise InvalidStateTransitionError(f"Cannot transition from {current_state} to {target_state}")

            # Invariants for specific states
            if target_state in [BenchmarkState.VALIDATION, BenchmarkState.REVIEW, BenchmarkState.PUBLISHED]:
                self._validate_invariants(benchmark)

            updated_benchmark = self.benchmark_repo.update(
                db_obj=benchmark, 
                obj_in={"status": target_state},
                commit=False
            )
            
            lifecycle_data = {
                "benchmark_id": benchmark.id,
                "state": target_state,
                "changed_by_id": user_id
            }
            self.lifecycle_repo.create(obj_in=lifecycle_data, commit=False)
            
            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(updated_benchmark)
            return updated_benchmark
        except Exception:
            self.benchmark_repo.db.rollback()
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

        if not getattr(active_version, 'dataset_bindings', None) and not hasattr(active_version, '_has_datasets'):
            raise InvariantViolationError("At least one valid dataset version must be linked.")
            
        if not getattr(active_version, 'evaluation_strategies', None) and not hasattr(active_version, '_has_evaluators'):
            raise InvariantViolationError("At least one evaluation strategy must be configured.")
            
        if not getattr(active_version, 'metrics', None) and not hasattr(active_version, '_has_metrics'):
            raise InvariantViolationError("At least one scoring metric must be defined.")

    def assert_editable(self, benchmark: Benchmark):
        """Ensure benchmark is not in an immutable state."""
        if benchmark.status in [BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE]:
            raise ImmutableVersionError(f"Cannot edit benchmark in {benchmark.status} state.")
