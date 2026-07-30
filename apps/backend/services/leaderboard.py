import uuid

from fastapi import HTTPException

from apps.backend.schemas.leaderboard import (
    LeaderboardEntryRead,
    LeaderboardRead,
    LeaderboardType,
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
