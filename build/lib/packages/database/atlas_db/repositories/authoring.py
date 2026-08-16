import uuid
from typing import Any

from atlas_db.models.authoring import (
    Benchmark,
    BenchmarkCategory,
    BenchmarkLifecycle,
    BenchmarkVersion,
    Capability,
)

from .base import BaseRepository


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

    def get_benchmarks_paginated(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_field: str | None = None,
        sort_order: str = "desc",
        project_id: uuid.UUID | None = None,
        owner_id: uuid.UUID | None = None,
        status: str | None = None,
        category_ids: list[uuid.UUID] | None = None,
        capability_ids: list[uuid.UUID] | None = None,
    ) -> tuple[list[Benchmark], int]:
        from atlas_db.repositories.query_utils import (
            apply_pagination,
            apply_sorting,
            get_paginated_results,
        )
        from typing import cast

        query = self.db.query(self.model)

        if project_id:
            query = query.filter(self.model.project_id == project_id)
        if owner_id:
            query = query.filter(self.model.author_id == owner_id)
        if status:
            query = query.filter(self.model.status == status)

        if category_ids:
            query = query.join(self.model.categories).filter(BenchmarkCategory.id.in_(category_ids))

        if capability_ids:
            query = query.join(self.model.capabilities).filter(Capability.id.in_(capability_ids))

        if sort_field:
            query = apply_sorting(query, self.model, sort_field, sort_order)
        else:
            # Default sort
            query = apply_sorting(query, self.model, "updated_at", "desc")

        return cast(tuple[list[Benchmark], int], get_paginated_results(query, limit, offset))


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
