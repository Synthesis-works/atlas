import uuid
from celery.utils.log import get_task_logger

from apps.backend.worker.celery_app import celery_app
from atlas_db.core.session import SessionLocal
from atlas_db.repositories.leaderboard import LeaderboardRepository
from atlas_db.repositories.authoring import (
    BenchmarkVersionRepository,
    CapabilityRepository,
)
from apps.backend.services.snapshot import LeaderboardSnapshotService

logger = get_task_logger(__name__)


@celery_app.task(name="tasks.generate_benchmark_snapshot")
def generate_benchmark_snapshot(
    benchmark_version_id_str: str, execution_id_trigger_str: str
) -> None:
    logger.info(
        f"Generating benchmark snapshot for {benchmark_version_id_str} triggered by {execution_id_trigger_str}"
    )

    with SessionLocal() as db:
        leaderboard_repo = LeaderboardRepository(db)
        snapshot_service = LeaderboardSnapshotService(db=db, leaderboard_repo=leaderboard_repo)

        benchmark_version_id = uuid.UUID(benchmark_version_id_str)
        execution_id_trigger = (
            uuid.UUID(execution_id_trigger_str) if execution_id_trigger_str else None
        )

        snapshot = snapshot_service.generate_benchmark_snapshot(
            benchmark_version_id=benchmark_version_id,
            reason="RUN_COMPLETED" if execution_id_trigger else "MANUAL_REFRESH",
            execution_id_trigger=execution_id_trigger,
        )
        if snapshot:
            logger.info(f"Successfully generated benchmark snapshot {snapshot.id}")
        else:
            logger.info(
                f"No snapshot generated (already exists or no data) for {benchmark_version_id_str}"
            )


@celery_app.task(name="tasks.generate_capability_snapshot")
def generate_capability_snapshot(capability_id_str: str, execution_id_trigger_str: str) -> None:
    logger.info(
        f"Generating capability snapshot for {capability_id_str} triggered by {execution_id_trigger_str}"
    )

    with SessionLocal() as db:
        leaderboard_repo = LeaderboardRepository(db)
        snapshot_service = LeaderboardSnapshotService(db=db, leaderboard_repo=leaderboard_repo)

        capability_id = uuid.UUID(capability_id_str)
        execution_id_trigger = (
            uuid.UUID(execution_id_trigger_str) if execution_id_trigger_str else None
        )

        snapshot = snapshot_service.generate_capability_snapshot(
            capability_id=capability_id,
            reason="RUN_COMPLETED" if execution_id_trigger else "MANUAL_REFRESH",
            execution_id_trigger=execution_id_trigger,
        )
        if snapshot:
            logger.info(f"Successfully generated capability snapshot {snapshot.id}")
        else:
            logger.info(
                f"No snapshot generated (already exists or no data) for {capability_id_str}"
            )
