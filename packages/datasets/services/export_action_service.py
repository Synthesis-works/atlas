import uuid
import structlog
from sqlalchemy.orm import Session
from datetime import datetime

from atlas_db.models.dataset import DatasetExportAction, DatasetExportState
from packages.datasets.services.export_service import DatasetExportService

logger = structlog.get_logger(__name__)

class ExportActionService:
    def __init__(self, db: Session, dataset_export_service: DatasetExportService):
        self.db = db
        self.export_service = dataset_export_service

    def schedule_export(self, dataset_version_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID | None = None) -> DatasetExportAction:
        """
        Creates (or retrieves an existing pending/running) export action.
        This provides strict idempotency bounds on duplicated asynchronous requests.
        """
        # PostgreSQL-backed idempotency check resolving active bounds
        import sqlalchemy

        action = DatasetExportAction(
            dataset_version_id=dataset_version_id,
            project_id=project_id,
            status=DatasetExportState.PENDING,
            created_by_id=user_id,
        )

        try:
            self.db.add(action)
            self.db.commit()
            self.db.refresh(action)
            return action
        except sqlalchemy.exc.IntegrityError:
            self.db.rollback()
            active_action = self.db.query(DatasetExportAction).filter(
                DatasetExportAction.dataset_version_id == dataset_version_id,
                DatasetExportAction.status.in_([DatasetExportState.PENDING, DatasetExportState.RUNNING])
            ).first()
            if active_action:
                logger.info("Retrieved existing active DatasetExportAction via constraint", action_id=str(active_action.id))
                return active_action

            action.status = DatasetExportState.FAILED
            action.error_message = "Unexpected concurrent termination"
            return action

    def process_export(self, action_id: uuid.UUID):
        """
        Execution abstraction converting a background Task state effectively gracefully natively.
        """
        action = self.db.query(DatasetExportAction).filter(DatasetExportAction.id == action_id).first()
        if not action:
            logger.warning("DatasetExportAction missing", action_id=str(action_id))
            return

        # Do not override currently running or completed structurally safely mapping
        if action.status not in (DatasetExportState.PENDING, DatasetExportState.FAILED):
            logger.warning("DatasetExportAction invalid transition", action_id=str(action_id), status=action.status)
            return

        action.status = DatasetExportState.RUNNING
        self.db.commit()

        try:
            uri = self.export_service.export_dataset(dataset_version_id=action.dataset_version_id, format_name="jsonl")

            action.artifact_uri = uri
            action.status = DatasetExportState.COMPLETED
            self.db.commit()

            logger.info("DatasetExportAction successfully completed", action_id=str(action_id))
        except Exception as e:
            action.status = DatasetExportState.FAILED
            action.error_message = str(e)
            self.db.commit()
            logger.error("DatasetExportAction failed", action_id=str(action_id), error=str(e), exc_info=True)
            raise e
