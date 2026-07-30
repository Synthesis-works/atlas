import uuid

from fastapi import HTTPException

from apps.backend.schemas.leaderboard import (
    LeaderboardEntryRead,
    LeaderboardRead,
    LeaderboardType,
    TrendPoint,
    ModelSummary,
    ModelBenchmarkHistory,
    ModelBenchmarkVersionHistory,
)
from apps.backend.schemas.query import PageResponse
from packages.database.atlas_db.repositories.authoring import (
    BenchmarkVersionRepository,
    CapabilityRepository,
)
from packages.database.atlas_db.repositories.leaderboard import LeaderboardRepository


class LeaderboardApplicationService:
    def __init__(
        self,
        leaderboard_repo: LeaderboardRepository,
        benchmark_version_repo: BenchmarkVersionRepository,
        capability_repo: CapabilityRepository,
    ):
        self.leaderboard_repo = leaderboard_repo
        self.benchmark_version_repo = benchmark_version_repo
        self.capability_repo = capability_repo

    def get_benchmark_leaderboard(
        self, benchmark_version_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> LeaderboardRead:
        """
        Retrieves the leaderboard for a specific benchmark version.
        """
        # Validate that benchmark version exists to return a clear 404
        bv = self.benchmark_version_repo.get(benchmark_version_id)
        if not bv:
            raise HTTPException(status_code=404, detail="Benchmark Version not found")

        # In a real system we'd join to Benchmark to get the name, but for now we'll
        # just construct it from the version string or fetch the benchmark if we want.
        # But this is fine for metadata.
        benchmark_name = f"Benchmark Version {bv.version_string}"

        raw_entries, total = self.leaderboard_repo.get_benchmark_leaderboard(
            benchmark_version_id=benchmark_version_id, limit=limit, offset=offset
        )

        entries = []
        for i, (model_name, overall_score, count, last_executed_at) in enumerate(raw_entries):
            entries.append(
                LeaderboardEntryRead(
                    rank=offset + i + 1,
                    model_name=model_name,
                    overall_score=overall_score,
                    benchmark_count=count,
                    last_updated=last_executed_at,
                    rank_delta=None,  # Real implementation would calculate this vs previous snapshot
                    metadata=None,
                )
            )

        page = PageResponse[LeaderboardEntryRead](
            items=entries,
            total=total,
            limit=limit,
            offset=offset,
        )

        return LeaderboardRead(
            leaderboard_type=LeaderboardType.BENCHMARK,
            title=benchmark_name,
            description=f"Leaderboard for Benchmark Version {bv.version_string}",
            benchmark_version_id=str(benchmark_version_id),
            capability_id=None,
            entries=page,
        )

    def get_capability_leaderboard(
        self, capability_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> LeaderboardRead:
        """
        Retrieves the leaderboard aggregated across all benchmarks for a specific capability.
        """
        cap = self.capability_repo.get(capability_id)
        if not cap:
            raise HTTPException(status_code=404, detail="Capability not found")

        raw_entries, total = self.leaderboard_repo.get_capability_leaderboard(
            capability_id=capability_id, limit=limit, offset=offset
        )

        entries = []
        for i, (model_name, overall_score, count, last_executed_at) in enumerate(raw_entries):
            entries.append(
                LeaderboardEntryRead(
                    rank=offset + i + 1,
                    model_name=model_name,
                    overall_score=overall_score,
                    benchmark_count=count,
                    last_updated=last_executed_at,
                    rank_delta=None,
                    metadata=None,
                )
            )

        page = PageResponse[LeaderboardEntryRead](
            items=entries,
            total=total,
            limit=limit,
            offset=offset,
        )

        return LeaderboardRead(
            leaderboard_type=LeaderboardType.CAPABILITY,
            title=cap.name,
            description=cap.description or f"Aggregated leaderboard for {cap.name} capability",
            capability_id=str(capability_id),
            benchmark_version_id=None,
            entries=page,
        )

    def get_model_history(self, target_model: str) -> list[TrendPoint]:
        raw_history = self.leaderboard_repo.get_model_history(target_model)

        points = []
        for created_at, score, bv_id, execution_id in raw_history:
            points.append(
                TrendPoint(
                    timestamp=created_at,
                    score=score,
                    rank=None,
                    benchmark_version=str(bv_id),
                    execution_id=str(execution_id),
                )
            )
        return points

    def get_model_benchmark_history(self, target_model: str) -> list[ModelBenchmarkHistory]:
        raw_history = self.leaderboard_repo.get_model_history(target_model)
        if not raw_history:
            return []

        # Group by benchmark version id
        from collections import defaultdict

        bv_points = defaultdict(list)
        for created_at, score, bv_id, execution_id in raw_history:
            bv_points[bv_id].append(
                TrendPoint(
                    timestamp=created_at,
                    score=score,
                    rank=None,
                    benchmark_version=None,
                    execution_id=str(execution_id)
                )
            )

        bv_ids = list(bv_points.keys())
        from packages.database.atlas_db.models.authoring import Benchmark, BenchmarkVersion

        # Fetch names and group by benchmark
        bvs = (
            self.benchmark_version_repo.db.query(BenchmarkVersion, Benchmark)
            .join(Benchmark, Benchmark.id == BenchmarkVersion.benchmark_id)
            .filter(BenchmarkVersion.id.in_(bv_ids))
            .all()
        )

        benchmarks_dict = defaultdict(list)
        for bv, b in bvs:
            history = bv_points[bv.id]
            benchmarks_dict[b.name].append(
                ModelBenchmarkVersionHistory(version_string=bv.version_string, history=history)
            )

        result = []
        for b_name, b_versions in benchmarks_dict.items():
            result.append(ModelBenchmarkHistory(benchmark_name=b_name, versions=b_versions))
        return result

    def get_model_rank_history(self, target_model: str) -> list[TrendPoint]:
        raw_history = self.leaderboard_repo.get_model_rank_history(target_model)
        points = []
        for timestamp, score, rank, target_type, target_id, execution_id in raw_history:
            points.append(
                TrendPoint(
                    timestamp=timestamp, score=score, rank=rank, benchmark_version=None, execution_id=str(execution_id)
                )
            )
        return points

    def get_model_summary(self, target_model: str) -> ModelSummary:
        benchmarks, best_rank, avg_rank, avg_score, last_exec, latest_delta = (
            self.leaderboard_repo.get_model_summary(target_model)
        )

        return ModelSummary(
            model=target_model,
            benchmarks=benchmarks,
            best_rank=best_rank,
            average_rank=avg_rank,
            average_score=avg_score,
            last_execution=last_exec,
            latest_delta=latest_delta,
        )

    def get_benchmark_history(self, benchmark_version_id: uuid.UUID) -> list[TrendPoint]:
        # Validate that benchmark version exists
        bv = self.benchmark_version_repo.get(benchmark_version_id)
        if not bv:
            raise HTTPException(status_code=404, detail="Benchmark Version not found")

        raw_history = self.leaderboard_repo.get_benchmark_history(benchmark_version_id)
        points = []
        for created_at, score, model_name, execution_id in raw_history:
            # Note: We overload benchmark_version field to return model_name for the endpoint's convenience
            points.append(
                TrendPoint(
                    timestamp=created_at,
                    score=score,
                    rank=None,
                    benchmark_version=model_name,
                    execution_id=str(execution_id),
                )
            )
        return points
