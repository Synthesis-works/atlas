import uuid
from sqlalchemy.orm import Session

from atlas_db.models.leaderboard import (
    LeaderboardSnapshot,
    LeaderboardSnapshotEntry,
    TargetType,
)
from atlas_db.repositories.leaderboard import LeaderboardRepository


class LeaderboardSnapshotService:
    def __init__(self, db: Session, leaderboard_repo: LeaderboardRepository):
        self.db = db
        self.leaderboard_repo = leaderboard_repo

    def generate_benchmark_snapshot(
        self,
        benchmark_version_id: uuid.UUID,
        reason: str,
        execution_id_trigger: uuid.UUID | None = None,
    ) -> LeaderboardSnapshot | None:
        """
        Generates a new snapshot for a benchmark version if one for the given trigger doesn't already exist.
        """
        if execution_id_trigger:
            # Idempotency check
            existing = (
                self.db.query(LeaderboardSnapshot)
                .filter(
                    LeaderboardSnapshot.target_type == TargetType.BENCHMARK_VERSION,
                    LeaderboardSnapshot.target_id == benchmark_version_id,
                    LeaderboardSnapshot.snapshot_reason == reason,
                )
                .all()
            )
            for ex in existing:
                if ex.metadata_json and ex.metadata_json.get("execution_id_trigger") == str(
                    execution_id_trigger
                ):
                    return ex  # Already generated for this trigger

        # Limit to 1000 to prevent unbound snapshot sizes
        raw_entries, total = self.leaderboard_repo.get_benchmark_leaderboard(
            benchmark_version_id=benchmark_version_id, limit=1000, offset=0
        )
        if not raw_entries:
            return None

        metadata = {}
        if execution_id_trigger:
            metadata["execution_id_trigger"] = str(execution_id_trigger)

        snapshot = LeaderboardSnapshot(
            target_type=TargetType.BENCHMARK_VERSION,
            target_id=benchmark_version_id,
            snapshot_reason=reason,
            metadata_json=metadata,
        )
        self.db.add(snapshot)
        self.db.flush()

        entries = []
        for i, (model_name, overall_score, count, last_executed_at, execution_id) in enumerate(
            raw_entries
        ):
            entries.append(
                LeaderboardSnapshotEntry(
                    snapshot_id=snapshot.id,
                    target_model=model_name,
                    rank=i + 1,
                    score=overall_score,
                    execution_id=execution_id,
                )
            )

        self.db.add_all(entries)
        self.db.commit()
        return snapshot

    def generate_capability_snapshot(
        self, capability_id: uuid.UUID, reason: str, execution_id_trigger: uuid.UUID | None = None
    ) -> LeaderboardSnapshot | None:
        """
        Generates a new snapshot for a capability if one for the given trigger doesn't already exist.
        """
        if execution_id_trigger:
            existing = (
                self.db.query(LeaderboardSnapshot)
                .filter(
                    LeaderboardSnapshot.target_type == TargetType.CAPABILITY,
                    LeaderboardSnapshot.target_id == capability_id,
                    LeaderboardSnapshot.snapshot_reason == reason,
                )
                .all()
            )
            for ex in existing:
                if ex.metadata_json and ex.metadata_json.get("execution_id_trigger") == str(
                    execution_id_trigger
                ):
                    return ex

        raw_entries, total = self.leaderboard_repo.get_capability_leaderboard(
            capability_id=capability_id, limit=1000, offset=0
        )
        if not raw_entries:
            return None

        metadata = {}
        if execution_id_trigger:
            metadata["execution_id_trigger"] = str(execution_id_trigger)

        snapshot = LeaderboardSnapshot(
            target_type=TargetType.CAPABILITY,
            target_id=capability_id,
            snapshot_reason=reason,
            metadata_json=metadata,
        )
        self.db.add(snapshot)
        self.db.flush()

        entries = []
        for i, (model_name, overall_score, count, last_executed_at, execution_id) in enumerate(
            raw_entries
        ):
            entries.append(
                LeaderboardSnapshotEntry(
                    snapshot_id=snapshot.id,
                    target_model=model_name,
                    rank=i + 1,
                    score=overall_score,
                    execution_id=execution_id,
                )
            )

        self.db.add_all(entries)
        self.db.commit()
        return snapshot
