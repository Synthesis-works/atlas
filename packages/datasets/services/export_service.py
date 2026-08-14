import uuid
import tempfile
import os
import structlog
from typing import Mapping

from packages.database.atlas_db.services.dataset_extraction import DatasetExtractionService
from packages.datasets.exporters.base import DatasetExporter
from packages.datasets.infrastructure.artifact_store import BaseTrainingArtifactStore
from packages.datasets.exporters.jsonl_exporter import JSONLDatasetExporter

logger = structlog.get_logger(__name__)

class DatasetExportService:
    """
    Consumer wrapper isolating D2 logic from physical storage layers.
    Consumes DatasetExtractionService, invokes JSON L exporters seamlessly tracking.
    """
    def __init__(
        self,
        extraction_service: DatasetExtractionService,
        artifact_store: BaseTrainingArtifactStore,
        exporters: Mapping[str, DatasetExporter] = None
    ):
        self.extraction_service = extraction_service
        self.artifact_store = artifact_store
        
        self.exporters = exporters or {
            "jsonl": JSONLDatasetExporter()
        }

    def export_dataset(self, dataset_version_id: uuid.UUID, format_name: str = "jsonl") -> str:
        """
        Exports a dataset version safely consuming the canonical abstraction.
        Returns the logical artifact URI.
        """
        if format_name not in self.exporters:
            raise ValueError(f"Unsupported export format: {format_name}")
            
        exporter = self.exporters[format_name]
        
        try:
            # Phase D2 -> Canonical Data Extraction
            examples = self.extraction_service.get_training_examples(dataset_version_id)
            if not examples:
                logger.warning("Empty dataset exported", dataset_version_id=str(dataset_version_id))
            
            # Phase D3 -> Export formulation
            result = exporter.export(examples)
            
            # Atomic artifact storage 
            filename = f"dataset_{dataset_version_id}.{result.filename_extension}"
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = os.path.join(tmp_dir, filename)
                with open(tmp_path, "wb") as f:
                    f.write(result.content)
                
                uri = self.artifact_store.store_training_artifact(
                    dataset_version_id=dataset_version_id,
                    name=filename,
                    source_path=tmp_path
                )
                
            return uri
        except Exception as e:
            logger.error("Failed to export dataset", dataset_version_id=str(dataset_version_id), error=str(e))
            raise RuntimeError(f"Export strictly failed: {e}") from e
