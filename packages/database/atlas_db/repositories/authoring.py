from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from .base import BaseRepository
from atlas_db.models.authoring import Benchmark, BenchmarkVersion, BenchmarkLifecycle, BenchmarkCategory, Capability, BenchmarkState

class ImmutableEntityError(Exception):
    pass

class BenchmarkRepository(BaseRepository[Benchmark]):
    model = Benchmark

    def get_for_update(self, id: Any) -> Benchmark | None:
        return self.db.query(self.model).filter(self.model.id == id).with_for_update().first()

    def update(self, *, db_obj: Benchmark, obj_in: dict, commit: bool = True) -> Benchmark:
        # Enforce domain invariant: cannot update published/archived benchmarks 
        # (unless we're transitioning state to archive, etc., but we shouldn't change core fields)
        # Actually, status transition is an update itself. Let's just allow it for now, 
        # or verify if non-status fields are changing when published. 
        # But a safer bet is to rely on BenchmarkService for field-level immutability.
        # But to be strict, if the benchmark is PUBLISHED and we are updating something other than status to ARCHIVE, we could block it.
        # Let's keep it simple and just do the update since BenchmarkService handles field-level checks.
        return super().update(db_obj=db_obj, obj_in=obj_in, commit=commit)

class BenchmarkVersionRepository(BaseRepository[BenchmarkVersion]):
    model = BenchmarkVersion
    
    def get_for_update(self, id: Any) -> BenchmarkVersion | None:
        return self.db.query(self.model).filter(self.model.id == id).with_for_update().first()

class BenchmarkLifecycleRepository(BaseRepository[BenchmarkLifecycle]):
    model = BenchmarkLifecycle

class BenchmarkCategoryRepository(BaseRepository[BenchmarkCategory]):
    model = BenchmarkCategory

class CapabilityRepository(BaseRepository[Capability]):
    model = Capability
