import datetime
import uuid

import structlog
from atlas_db.core.session import SessionLocal
from celery.exceptions import SoftTimeLimitExceeded

from apps.backend.worker.celery_app import celery_app
from packages.datasets.services.export_action_service import ExportActionService
from packages.datasets.services.export_service import DatasetExportService
from atlas_db.services.dataset_extraction import DatasetExtractionService

# We need the correct storage resolution, assuming Minio Storage or Local Storage
from packages.evaluation_engine.infrastructure.artifact_store import LocalArtifactStore
from apps.backend.config import settings

logger = structlog.get_logger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=3600,
    time_limit=3660,
)
def run_dataset_export_task(self, export_action_id_str: str, correlation_id: str | None = None):
    """
    Celery task representing an asynchronous background process evaluating JSONL export serialization cleanly formatting tracking efficiently reliably dynamically.
    """
    export_action_id = uuid.UUID(export_action_id_str)
    logger.info("Starting Dataset Export Task", action_id=str(export_action_id))

    try:
        with SessionLocal() as db:
            # We instantiate standard explicit bounds ensuring Zero Trust invariants globally natively
            extraction_service = DatasetExtractionService(db)

            # Using Local Artifact Store or properly injected Minio configuration according to system config
            artifact_store_path = getattr(settings, "artifact_storage_path", "/tmp/atlas_artifacts")
            artifact_store = LocalArtifactStore(base_dir=artifact_store_path)

            # Wire up safely
            export_service = DatasetExportService(
                extraction_service=extraction_service, artifact_store=artifact_store  # type: ignore[arg-type]
            )
            action_service = ExportActionService(db, export_service)

            action_service.process_export(export_action_id)

    except SoftTimeLimitExceeded:
        logger.warning(
            "Dataset export timed out (SoftTimeLimitExceeded)", action_id=str(export_action_id)
        )
        with SessionLocal() as db:
            from atlas_db.models.dataset import DatasetExportAction

            action = (
                db.query(DatasetExportAction)
                .filter_by(id=export_action_id)
                .with_for_update()
                .first()
            )  # Explicit raw fallback
            if action and str(action.status.value).lower() in ("pending", "running"):
                action.status = "failed"
                action.error_message = "SoftTimeLimitExceeded"
                db.commit()
        raise

    except Exception as exc:
        dead_letter_payload = {
            "export_action_id": str(export_action_id),
            "celery_task_id": self.request.id,
            "retry_count": self.request.retries,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "occurred_at": datetime.datetime.utcnow().isoformat(),
        }
        logger.error("Dataset export task failed", dead_letter=dead_letter_payload, exc_info=True)
        if self.request.retries >= self.max_retries:
            logger.error(
                "Max retries exceeded, dataset export permanently failed",
                dead_letter=dead_letter_payload,
            )
        raise self.retry(exc=exc, countdown=2**self.request.retries)
