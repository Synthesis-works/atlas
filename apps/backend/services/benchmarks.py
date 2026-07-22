import uuid

from atlas_db.repositories.authoring import (
    BenchmarkCategoryRepository,
    BenchmarkRepository,
    CapabilityRepository,
)
from atlas_db.services.benchmark_service import (
    BenchmarkService,
    ConcurrencyViolationError,
    ImmutableVersionError,
    InvalidStateTransitionError,
    InvariantViolationError,
    PermissionDeniedError,
)
from fastapi import HTTPException, status

from apps.backend.schemas.benchmarks import (
    BenchmarkCreate,
    BenchmarkRead,
    BenchmarkUpdate,
    BenchmarkVersionCreate,
    BenchmarkVersionRead,
    BenchmarkVersionUpdate,
)


def map_domain_error(e: Exception):
    if isinstance(e, PermissionDeniedError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    elif isinstance(e, InvalidStateTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    elif isinstance(e, InvariantViolationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    elif isinstance(e, ConcurrencyViolationError) or isinstance(e, ImmutableVersionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error"
        )


class BenchmarkApplicationService:
    def __init__(
        self,
        domain_service: BenchmarkService,
        benchmark_repo: BenchmarkRepository,
        category_repo: BenchmarkCategoryRepository,
        capability_repo: CapabilityRepository,
    ):
        self.domain_service = domain_service
        self.benchmark_repo = benchmark_repo
        self.category_repo = category_repo
        self.capability_repo = capability_repo

    def create_benchmark(
        self, project_id: uuid.UUID, author_id: uuid.UUID, data: BenchmarkCreate
    ) -> BenchmarkRead:
        try:
            benchmark, events = self.domain_service.create_benchmark(
                project_id=data.project_id,
                author_id=author_id,
                name=data.name,
                objective=data.objective,
                difficulty=data.difficulty,
                domain=data.domain,
                type=data.type,
                visibility=data.visibility,
            )

            for event in events:
                print(f"Audit Event: {event}")

            # Associate categories and capabilities
            if data.category_ids:
                categories = []
                for cat_id in data.category_ids:
                    cat = self.category_repo.get(cat_id)
                    if cat:
                        categories.append(cat)
                benchmark.categories = categories

            if data.capability_ids:
                capabilities = []
                for cap_id in data.capability_ids:
                    cap = self.capability_repo.get(cap_id)
                    if cap:
                        capabilities.append(cap)
                benchmark.capabilities = capabilities

            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(benchmark)

            return BenchmarkRead(
                id=benchmark.id,
                project_id=benchmark.project_id,
                state=benchmark.status,
                name=benchmark.name,
            )
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def get_benchmarks(self, project_id: uuid.UUID) -> list[BenchmarkRead]:
        benchmarks = (
            self.benchmark_repo.db.query(self.benchmark_repo.model)
            .filter(self.benchmark_repo.model.project_id == project_id)
            .all()
        )
        return [
            BenchmarkRead(id=b.id, project_id=b.project_id, state=b.status, name=b.name)
            for b in benchmarks
        ]

    def get_benchmark(self, benchmark_id: uuid.UUID) -> BenchmarkRead:
        benchmark = self.benchmark_repo.get(benchmark_id)
        if not benchmark:
            raise HTTPException(status_code=404, detail="Benchmark not found")

        return BenchmarkRead(
            id=benchmark.id,
            project_id=benchmark.project_id,
            state=benchmark.status,
            name=benchmark.name,
        )

    def update_benchmark(
        self, benchmark_id: uuid.UUID, user_id: uuid.UUID, user_role: str, data: BenchmarkUpdate
    ) -> BenchmarkRead:
        try:
            benchmark = self.benchmark_repo.get_for_update(benchmark_id)
            if not benchmark:
                raise HTTPException(status_code=404, detail="Benchmark not found")

            if not self.domain_service.can_edit(benchmark, user_id, user_role):
                raise PermissionDeniedError("User does not have permission to edit this benchmark")
            self.domain_service.assert_editable(benchmark)

            update_data = data.model_dump(exclude_unset=True)

            if "category_ids" in update_data:
                categories = []
                for cat_id in update_data["category_ids"]:
                    cat = self.category_repo.get(cat_id)
                    if cat:
                        categories.append(cat)
                benchmark.categories = categories
                del update_data["category_ids"]

            if "capability_ids" in update_data:
                capabilities = []
                for cap_id in update_data["capability_ids"]:
                    cap = self.capability_repo.get(cap_id)
                    if cap:
                        capabilities.append(cap)
                benchmark.capabilities = capabilities
                del update_data["capability_ids"]

            self.benchmark_repo.update(db_obj=benchmark, obj_in=update_data, commit=False)
            self.benchmark_repo.db.commit()
            self.benchmark_repo.db.refresh(benchmark)

            return BenchmarkRead(
                id=benchmark.id,
                project_id=benchmark.project_id,
                state=benchmark.status,
                name=benchmark.name,
            )
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def delete_benchmark(self, benchmark_id: uuid.UUID, user_id: uuid.UUID, user_role: str):
        try:
            benchmark = self.benchmark_repo.get_for_update(benchmark_id)
            if not benchmark:
                raise HTTPException(status_code=404, detail="Benchmark not found")

            if not self.domain_service.can_edit(benchmark, user_id, user_role):
                raise PermissionDeniedError(
                    "User does not have permission to delete this benchmark"
                )
            self.domain_service.assert_editable(benchmark)

            self.benchmark_repo.delete(id=benchmark_id, hard=False, commit=True)
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def create_version(
        self,
        benchmark_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        data: BenchmarkVersionCreate,
    ) -> BenchmarkVersionRead:
        try:
            version, events = self.domain_service.create_version(
                benchmark_id=benchmark_id,
                version_string=data.version_string,
                user_id=user_id,
                user_role=user_role,
                dataset_version_ids=data.dataset_version_ids,
                evaluation_strategy_id=data.evaluation_strategy_id,
            )

            for event in events:
                print(f"Audit Event: {event}")

            benchmark = self.benchmark_repo.get(benchmark_id)

            return BenchmarkVersionRead(
                id=version.id,
                benchmark_id=version.benchmark_id,
                version_string=version.version_string,
                state=benchmark.status,
                dataset_version_ids=[dv.id for dv in version.dataset_versions]
                if version.dataset_versions
                else [],
                evaluation_strategy_id=version.evaluation_strategy_id,
            )
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def get_versions(self, benchmark_id: uuid.UUID) -> list[BenchmarkVersionRead]:
        benchmark = self.benchmark_repo.get(benchmark_id)
        if not benchmark:
            raise HTTPException(status_code=404, detail="Benchmark not found")

        versions = (
            self.benchmark_repo.db.query(self.domain_service.version_repo.model)
            .filter_by(benchmark_id=benchmark_id)
            .all()
        )
        return [
            BenchmarkVersionRead(
                id=v.id,
                benchmark_id=v.benchmark_id,
                version_string=v.version_string,
                state=benchmark.status,
                dataset_version_ids=[dv.id for dv in v.dataset_versions]
                if v.dataset_versions
                else [],
                evaluation_strategy_id=v.evaluation_strategy_id,
            )
            for v in versions
        ]

    def update_version(
        self,
        version_id: uuid.UUID,
        user_id: uuid.UUID,
        user_role: str,
        data: BenchmarkVersionUpdate,
    ) -> BenchmarkVersionRead:
        try:
            version, events = self.domain_service.update_version(
                version_id=version_id,
                user_id=user_id,
                user_role=user_role,
                dataset_version_ids=data.dataset_version_ids,
                evaluation_strategy_id=data.evaluation_strategy_id,
            )

            for event in events:
                print(f"Audit Event: {event}")

            benchmark = self.benchmark_repo.get(version.benchmark_id)

            return BenchmarkVersionRead(
                id=version.id,
                benchmark_id=version.benchmark_id,
                version_string=version.version_string,
                state=benchmark.status,
                dataset_version_ids=[dv.id for dv in version.dataset_versions]
                if version.dataset_versions
                else [],
                evaluation_strategy_id=version.evaluation_strategy_id,
            )
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def validate_version(self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str):
        try:
            version, events = self.domain_service.validate_version(version_id, user_id, user_role)
            for event in events:
                print(f"Audit Event: {event}")
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def publish_version(self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str):
        try:
            version, events = self.domain_service.publish_version(version_id, user_id, user_role)
            for event in events:
                print(f"Audit Event: {event}")
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def archive_version(self, version_id: uuid.UUID, user_id: uuid.UUID, user_role: str):
        try:
            version, events = self.domain_service.archive_version(version_id, user_id, user_role)
            for event in events:
                print(f"Audit Event: {event}")
        except HTTPException:
            self.benchmark_repo.db.rollback()
            raise
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)
