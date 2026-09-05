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
    BenchmarkFilterRequest,
    BenchmarkRead,
    BenchmarkSortField,
    BenchmarkUpdate,
    BenchmarkVersionCreate,
    BenchmarkVersionRead,
    BenchmarkVersionUpdate,
)
from apps.backend.schemas.query import PageRequest, PageResponse, SortRequest


from typing import NoReturn

import logging

logger = logging.getLogger(__name__)


def _normalize_fraction(value: float) -> float:
    """Collapse legacy 0-100 telemetry into the canonical 0-1 score contract."""
    return value / 100.0 if value > 1.0 else value


def map_domain_error(e: Exception) -> NoReturn:
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


def _map_benchmark_to_read(b, db=None) -> BenchmarkRead:
    from datetime import datetime

    versions_read: list[BenchmarkVersionRead] = []
    version_ids = []
    primary_dataset_id = None
    primary_dataset_version_id = None

    if hasattr(b, "versions") and b.versions:
        for v in b.versions:
            if hasattr(v, "id"):
                version_ids.append(v.id)
            dataset_version_ids = []
            if hasattr(v, "dataset_versions") and v.dataset_versions:
                dataset_version_ids = [dv.id for dv in v.dataset_versions if hasattr(dv, "id")]
            elif hasattr(v, "primary_dataset_version_id") and v.primary_dataset_version_id:
                dataset_version_ids = [v.primary_dataset_version_id]
            
            if not primary_dataset_version_id and dataset_version_ids:
                primary_dataset_version_id = dataset_version_ids[0]

            versions_read.append(
                BenchmarkVersionRead(
                    id=v.id,
                    benchmark_id=v.benchmark_id,
                    version_string=v.version_string,
                    state=str(b.status or "READY"),
                    dataset_version_ids=dataset_version_ids,
                    evaluation_strategy_id=getattr(v, "evaluation_strategy_id", None),
                )
            )

    evaluation_case_count = None
    execution_count = None
    completed_execution_count = None
    failed_execution_count = None
    evaluation_count = None
    passed_evaluation_count = None
    average_score = None
    latest_score = None
    latest_execution_at = None
    average_latency_ms = None

    if db and version_ids:
        try:
            from atlas_db.models.execution import Execution, ExecutionStatus, ModelOutput
            from atlas_db.models.tasks import TestCase
            from atlas_db.models.evaluation import EvaluationResult
            from atlas_db.models.dataset import DatasetVersion
            from sqlalchemy import func

            # Execution metrics
            executions = db.query(Execution).filter(Execution.benchmark_version_id.in_(version_ids)).all()
            if executions:
                execution_count = len(executions)
                completed_execution_count = sum(1 for e in executions if e.status == ExecutionStatus.COMPLETED)
                failed_execution_count = sum(1 for e in executions if e.status in (ExecutionStatus.FAILED, ExecutionStatus.TIMED_OUT))

                sorted_execs = sorted(executions, key=lambda e: e.created_at or datetime.min, reverse=True)
                latest_exec = sorted_execs[0]
                latest_execution_at = latest_exec.created_at

                exec_ids = [e.id for e in executions]

                # Evaluation results
                eval_results = (
                    db.query(EvaluationResult)
                    .join(ModelOutput, ModelOutput.id == EvaluationResult.model_output_id)
                    .filter(ModelOutput.execution_id.in_(exec_ids))
                    .all()
                )
                if eval_results:
                    evaluation_count = len(eval_results)
                    passed_evaluation_count = sum(1 for r in eval_results if r.passed)
                    # Deterministic chronological order; the last result is the latest.
                    eval_results.sort(
                        key=lambda r: r.created_at or datetime.min, reverse=False
                    )
                    scores = []
                    for r in eval_results:
                        raw_score = None
                        raw_measurements = r.raw_measurements
                        if (
                            isinstance(raw_measurements, dict)
                            and "score" in raw_measurements
                        ):
                            try:
                                raw_score = float(raw_measurements["score"])
                            except (ValueError, TypeError):
                                raw_score = None
                        # Never fabricate a numeric score from thin air; a binary
                        # pass/fail is the only deterministic extrapolation.
                        if raw_score is None:
                            raw_score = 1.0 if r.passed else 0.0
                        scores.append(_normalize_fraction(raw_score))
                    if scores:
                        average_score = round(sum(scores) / len(scores), 2)
                        latest_score = round(scores[-1], 2)
                elif latest_exec.execution_config and "pass_at_1" in latest_exec.execution_config:
                    try:
                        pass_at_1 = _normalize_fraction(
                            float(latest_exec.execution_config["pass_at_1"])
                        )
                        average_score = round(pass_at_1, 2)
                        latest_score = average_score
                    except (ValueError, TypeError):
                        pass

                # Average latency
                latencies = [
                    mo[0]
                    for mo in db.query(ModelOutput.duration_ms)
                    .filter(ModelOutput.execution_id.in_(exec_ids), ModelOutput.duration_ms.isnot(None))
                    .all()
                    if mo[0] is not None
                ]
                if latencies:
                    average_latency_ms = round(sum(latencies) / len(latencies), 1)

            # Test case count
            all_dv_ids = []
            for v in versions_read:
                if v.dataset_version_ids:
                    all_dv_ids.extend(v.dataset_version_ids)
            if all_dv_ids:
                evaluation_case_count = (
                    db.query(func.count(TestCase.id))
                    .filter(TestCase.dataset_version_id.in_(set(all_dv_ids)))
                    .scalar()
                    or 0
                )

            # Primary dataset id
            if primary_dataset_version_id:
                dv = db.query(DatasetVersion).filter(DatasetVersion.id == primary_dataset_version_id).first()
                if dv:
                    primary_dataset_id = dv.dataset_id
        except Exception:
            # Maintain strict error resilience while returning persisted fields,
            # but surface the failure in telemetry instead of swallowing it.
            logger.warning("Failed to enrich benchmark telemetry", exc_info=True)

    return BenchmarkRead(
        id=b.id,
        project_id=b.project_id,
        state=str(b.status or "READY"),
        name=b.name,
        objective=getattr(b, "objective", None),
        domain=getattr(b, "domain", None),
        difficulty=getattr(b, "difficulty", None),
        type=getattr(b, "type", None),
        created_at=getattr(b, "created_at", None),
        updated_at=getattr(b, "updated_at", None),
        versions=versions_read,
        primary_dataset_id=primary_dataset_id,
        primary_dataset_version_id=primary_dataset_version_id,
        evaluation_case_count=evaluation_case_count,
        execution_count=execution_count,
        completed_execution_count=completed_execution_count,
        failed_execution_count=failed_execution_count,
        evaluation_count=evaluation_count,
        passed_evaluation_count=passed_evaluation_count,
        average_score=average_score,
        latest_score=latest_score,
        latest_execution_at=latest_execution_at,
        average_latency_ms=average_latency_ms,
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
            # Domain service handles invariant validation and creation logic
            benchmark, events = self.domain_service.create_benchmark(
                project_id=project_id,
                author_id=author_id,
                name=data.name,
                objective=data.objective,
            )

            for event in events:
                # Mock bus emission or structured logging
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

            return _map_benchmark_to_read(benchmark, self.benchmark_repo.db)
        except Exception as e:
            self.benchmark_repo.db.rollback()
            map_domain_error(e)

    def get_benchmarks_paginated(
        self,
        page_req: PageRequest,
        sort_req: SortRequest[BenchmarkSortField],
        filter_req: BenchmarkFilterRequest,
        project_id: uuid.UUID | None = None,
    ) -> PageResponse[BenchmarkRead]:
        status_val = filter_req.status.value if filter_req.status else None

        benchmarks, total = self.benchmark_repo.get_benchmarks_paginated(
            limit=page_req.limit,
            offset=page_req.offset or 0,
            sort_field=sort_req.sort.value if sort_req.sort else None,
            sort_order=sort_req.order,
            project_id=project_id,
            owner_id=filter_req.owner_id,
            status=status_val,
            category_ids=filter_req.category_ids,
            capability_ids=filter_req.capability_ids,
        )
        items = [_map_benchmark_to_read(b, self.benchmark_repo.db) for b in benchmarks]
        return PageResponse(
            items=items,
            total=total,
            limit=page_req.limit,
            offset=page_req.offset,
        )

    def get_recent_benchmarks(self, limit: int = 10) -> list[BenchmarkRead]:
        # A convenience method for the recent history endpoint
        # Fetches benchmarks globally, ordered by updated_at desc
        benchmarks, _ = self.benchmark_repo.get_benchmarks_paginated(
            limit=limit,
            offset=0,
            sort_field="updated_at",
            sort_order="desc",
        )
        return [_map_benchmark_to_read(b, self.benchmark_repo.db) for b in benchmarks]

    def get_benchmark(self, benchmark_id: uuid.UUID) -> BenchmarkRead:
        benchmark = self.benchmark_repo.get(benchmark_id)
        if not benchmark:
            raise HTTPException(status_code=404, detail="Benchmark not found")

        return _map_benchmark_to_read(benchmark, self.benchmark_repo.db)

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

            return _map_benchmark_to_read(benchmark, self.benchmark_repo.db)
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
