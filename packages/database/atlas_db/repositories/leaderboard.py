import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from atlas_db.models.execution import Execution
from atlas_db.models.evaluation import CapabilityProfile

from .base import BaseRepository


class LeaderboardRepository(BaseRepository[Execution]):
    model = Execution

    def get_benchmark_leaderboard(
        self,
        benchmark_version_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[str, float, int, Any]], int]:
        """
        Ranks models on a specific benchmark version based on their latest successful execution.

        Returns:
            Tuple of (list of (target_model, overall_score, benchmark_count, last_executed_at), total_count)
        """
        # Step 1: CTE to get the latest successful execution ID per model for this benchmark
        # We use PostgreSQL DISTINCT ON which is highly efficient for this.
        # However, to be dialect-agnostic in SQLAlchemy (or if we must), we could use ROW_NUMBER()
        # Since PostgreSQL is assumed based on the spec, we will use DISTINCT ON via SQLAlchemy.

        # We'll use a subquery to find the latest execution per model
        # using the distinct() and order_by() to get the first row per group.
        # SQLAlchemy supports distinct(Execution.target_model) which translates to DISTINCT ON in Postgres.

        latest_executions_subq = (
            self.db.query(Execution.id)
            .filter(
                Execution.benchmark_version_id == benchmark_version_id,
                Execution.status == "COMPLETED",
            )
            .distinct(Execution.target_model)
            .order_by(Execution.target_model, Execution.created_at.desc())
            .subquery()
        )

        # Step 2: Main query joining the filtered executions with capability profiles
        query = (
            self.db.query(
                Execution.target_model,
                CapabilityProfile.overall_score,
                func.count()
                .over()
                .label("total_count"),  # Window function to get total rows without a separate query
                Execution.created_at.label("last_executed_at"),
            )
            .join(CapabilityProfile, CapabilityProfile.execution_id == Execution.id)
            .filter(Execution.id.in_(latest_executions_subq))
            # Tie-breaking hierarchy:
            .order_by(
                CapabilityProfile.overall_score.desc(),
                Execution.created_at.desc(),
                Execution.id.asc(),
            )
        )

        # Fetching paginated results manually since we embedded total_count
        results = query.offset(offset).limit(limit).all()

        if not results:
            return [], 0

        total = results[0][2]

        # Format the output: target_model, overall_score, benchmark_count, last_executed_at
        # Benchmark count is always 1 for a benchmark leaderboard entry
        formatted_results = [(row[0], row[1], 1, row[3]) for row in results]

        return formatted_results, total

    def get_capability_leaderboard(
        self,
        capability_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[str, float, int, Any]], int]:
        """
        Ranks models across all benchmarks mapped to a specific capability.
        """
        # In a real implementation, we would join with BenchmarkCapability.
        # Since we don't have the BenchmarkCapability mapping explicitly in the imports yet,
        # we will use the CapabilityScore which links CapabilityProfile to Capability.
        from atlas_db.models.evaluation import CapabilityScore

        # CTE to get latest execution per (target_model, benchmark_version_id)
        latest_executions_subq = (
            self.db.query(Execution.id)
            .filter(Execution.status == "COMPLETED")
            # Distinct on model AND benchmark to get latest score per benchmark for each model
            .distinct(Execution.target_model, Execution.benchmark_version_id)
            .order_by(
                Execution.target_model, Execution.benchmark_version_id, Execution.created_at.desc()
            )
            .subquery()
        )

        # To avoid window function in group_by which can be complex, let's use a simpler total count query
        # Actually, let's do standard separate count to be safe.
        count_query = (
            self.db.query(func.count(func.distinct(Execution.target_model)))
            .join(CapabilityProfile, CapabilityProfile.execution_id == Execution.id)
            .join(CapabilityScore, CapabilityScore.capability_profile_id == CapabilityProfile.id)
            .filter(
                Execution.id.in_(latest_executions_subq),
                CapabilityScore.capability_id == capability_id,
            )
        )
        total = count_query.scalar() or 0

        # Remove total_count from main query projection
        main_query = (
            self.db.query(
                Execution.target_model,
                func.avg(CapabilityScore.score).label("avg_capability_score"),
                func.count(Execution.benchmark_version_id.distinct()).label("benchmark_count"),
                func.max(Execution.created_at).label("last_executed_at"),
            )
            .join(CapabilityProfile, CapabilityProfile.execution_id == Execution.id)
            .join(CapabilityScore, CapabilityScore.capability_profile_id == CapabilityProfile.id)
            .filter(
                Execution.id.in_(latest_executions_subq),
                CapabilityScore.capability_id == capability_id,
            )
            .group_by(Execution.target_model)
            .order_by(
                func.avg(CapabilityScore.score).desc(),
                func.max(Execution.created_at).desc(),
                Execution.target_model.asc(),
            )
            .offset(offset)
            .limit(limit)
        )

        results = main_query.all()
        formatted_results = [(row[0], float(row[1]), row[2], row[3]) for row in results]

        return formatted_results, total

    def get_model_history(self, target_model: str) -> list[tuple[Any, float, uuid.UUID, uuid.UUID]]:
        """
        Retrieves raw score evolution for a model across all benchmark versions.
        Ordered chronologically (oldest to newest).
        """
        query = (
            self.db.query(
                Execution.created_at,
                CapabilityProfile.overall_score,
                Execution.benchmark_version_id,
                Execution.id,
            )
            .join(CapabilityProfile, CapabilityProfile.execution_id == Execution.id)
            .filter(Execution.target_model == target_model, Execution.status == "COMPLETED")
            .order_by(Execution.created_at.asc())
        )
        return query.all()

    def get_benchmark_history(
        self, benchmark_version_id: uuid.UUID
    ) -> list[tuple[Any, float, str, uuid.UUID]]:
        """
        Retrieves raw score evolution for all models on a specific benchmark version.
        Ordered chronologically (oldest to newest).
        """
        query = (
            self.db.query(
                Execution.created_at,
                CapabilityProfile.overall_score,
                Execution.target_model,
                Execution.id,
            )
            .join(CapabilityProfile, CapabilityProfile.execution_id == Execution.id)
            .filter(
                Execution.benchmark_version_id == benchmark_version_id,
                Execution.status == "COMPLETED",
            )
            .order_by(Execution.created_at.asc())
        )
        return query.all()

    def get_model_rank_history(
        self, target_model: str
    ) -> list[tuple[Any, float, int, Any, uuid.UUID, uuid.UUID]]:
        """
        Retrieves rank history for a model from Leaderboard Snapshots.
        Ordered chronologically.
        """
        from atlas_db.models.leaderboard import LeaderboardSnapshot, LeaderboardSnapshotEntry

        query = (
            self.db.query(
                LeaderboardSnapshot.snapshot_timestamp,
                LeaderboardSnapshotEntry.score,
                LeaderboardSnapshotEntry.rank,
                LeaderboardSnapshot.target_type,
                LeaderboardSnapshot.target_id,
                LeaderboardSnapshotEntry.execution_id,
            )
            .join(
                LeaderboardSnapshotEntry,
                LeaderboardSnapshotEntry.snapshot_id == LeaderboardSnapshot.id,
            )
            .filter(LeaderboardSnapshotEntry.target_model == target_model)
            .order_by(LeaderboardSnapshot.snapshot_timestamp.asc())
        )
        return query.all()

    def get_model_summary(
        self, target_model: str
    ) -> tuple[int, int | None, float | None, float | None, Any | None, int | None]:
        """
        Returns an aggregate summary for a model.
        (benchmarks_count, best_rank, avg_rank, avg_score, last_execution_time, latest_delta)
        """
        from atlas_db.models.leaderboard import LeaderboardSnapshotEntry

        # 1. Total distinct benchmarks evaluated
        benchmarks_count = (
            self.db.query(func.count(func.distinct(Execution.benchmark_version_id)))
            .filter(Execution.target_model == target_model, Execution.status == "COMPLETED")
            .scalar()
            or 0
        )

        # 2. Best rank and avg rank from snapshots
        rank_stats = (
            self.db.query(
                func.min(LeaderboardSnapshotEntry.rank), func.avg(LeaderboardSnapshotEntry.rank)
            )
            .filter(LeaderboardSnapshotEntry.target_model == target_model)
            .first()
        )
        best_rank = rank_stats[0] if rank_stats else None
        avg_rank = float(rank_stats[1]) if rank_stats and rank_stats[1] is not None else None

        # 3. Avg score from ALL executions
        avg_score = (
            self.db.query(func.avg(CapabilityProfile.overall_score))
            .join(Execution, CapabilityProfile.execution_id == Execution.id)
            .filter(Execution.target_model == target_model, Execution.status == "COMPLETED")
            .scalar()
        )
        avg_score = float(avg_score) if avg_score is not None else None

        # 4. Last execution time
        last_exec = (
            self.db.query(func.max(Execution.created_at))
            .filter(Execution.target_model == target_model, Execution.status == "COMPLETED")
            .scalar()
        )

        return benchmarks_count, best_rank, avg_rank, avg_score, last_exec, None
