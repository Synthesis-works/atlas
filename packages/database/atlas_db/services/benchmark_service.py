import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from atlas_db.models.authoring import (
    Benchmark, 
    BenchmarkState, 
    BenchmarkLifecycle, 
    BenchmarkVersion,
    BenchmarkCategory,
    Capability
)

class BenchmarkServiceError(Exception):
    """Base exception for BenchmarkService."""

class PermissionDeniedError(BenchmarkServiceError):
    """Raised when user does not have permission."""

class InvalidStateTransitionError(BenchmarkServiceError):
    """Raised when an invalid state transition is attempted."""

class ValidationError(BenchmarkServiceError):
    """Raised when validation rules are not met."""

class ImmutableVersionError(BenchmarkServiceError):
    """Raised when attempting to modify a published or archived benchmark version."""


class BenchmarkService:
    """Service layer for Benchmark Authoring (Phase A)."""

    def __init__(self, db: Session):
        self.db = db

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
        benchmark = Benchmark(
            project_id=project_id,
            author_id=author_id,
            name=name,
            objective=objective,
            difficulty=difficulty,
            domain=domain,
            type=type,
            visibility=visibility,
            status=BenchmarkState.PROPOSAL
        )
        self.db.add(benchmark)
        self.db.flush()

        lifecycle = BenchmarkLifecycle(
            benchmark_id=benchmark.id,
            state=BenchmarkState.PROPOSAL,
            changed_by_id=author_id
        )
        self.db.add(lifecycle)
        self.db.commit()
        self.db.refresh(benchmark)
        return benchmark

    def can_edit(self, benchmark: Benchmark, user_id: uuid.UUID, user_role: str) -> bool:
        """Check if user can edit unpublished versions."""
        if benchmark.status in [BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE]:
            return False
        # Org Admins or Project Write access
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
        benchmark: Benchmark,
        target_state: BenchmarkState,
        user_id: uuid.UUID,
        user_role: str
    ) -> Benchmark:
        """Transition benchmark state following the lifecycle engine rules."""
        
        current_state = BenchmarkState(benchmark.status)
        
        # Validate permissions based on target action
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

        # Invariant checks for specific states
        if target_state in [BenchmarkState.VALIDATION, BenchmarkState.REVIEW, BenchmarkState.PUBLISHED]:
            self._validate_invariants(benchmark)

        benchmark.status = target_state
        self.db.add(benchmark)
        
        lifecycle = BenchmarkLifecycle(
            benchmark_id=benchmark.id,
            state=target_state,
            changed_by_id=user_id
        )
        self.db.add(lifecycle)
        self.db.commit()
        self.db.refresh(benchmark)
        return benchmark

    def _validate_invariants(self, benchmark: Benchmark):
        """Validate invariant rules required for validation, review, and published states."""
        # Taxonomy check
        if not benchmark.categories:
            raise ValidationError("Benchmark must have at least one Category assigned.")
        if not benchmark.capabilities:
            raise ValidationError("Benchmark must have at least one Capability assigned.")

        # Since active editable version dataset bindings/evaluators/metrics aren't firmly 
        # defined in the base schema, we assume they exist as dynamic collections or check versions.
        # We find the active version (the latest draft version). 
        # For slice 1A we verify the logical constraint.
        
        active_version = None
        if benchmark.versions:
            # Assumes the latest version is the active editable version if not published
            active_version = benchmark.versions[-1]
            
        if not active_version:
            raise ValidationError("Benchmark must have an active version for validation.")

        # In a complete schema, we'd check active_version.dataset_bindings, etc.
        # As a stub for invariant rules mentioned in specification:
        if not getattr(active_version, 'dataset_bindings', None) and not hasattr(active_version, '_has_datasets'):
            raise ValidationError("At least one valid dataset version must be linked.")
            
        if not getattr(active_version, 'evaluation_strategies', None) and not hasattr(active_version, '_has_evaluators'):
            raise ValidationError("At least one evaluation strategy must be configured.")
            
        if not getattr(active_version, 'metrics', None) and not hasattr(active_version, '_has_metrics'):
            raise ValidationError("At least one scoring metric must be defined.")

    def assert_editable(self, benchmark: Benchmark):
        """Ensure benchmark is not in an immutable state."""
        if benchmark.status in [BenchmarkState.PUBLISHED, BenchmarkState.ARCHIVE]:
            raise ImmutableVersionError(f"Cannot edit benchmark in {benchmark.status} state.")
