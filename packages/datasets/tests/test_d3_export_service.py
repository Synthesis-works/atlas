import uuid
import json
import pytest
from packages.datasets.models import TrainingExample
from packages.datasets.services.export_service import DatasetExportService
from packages.datasets.infrastructure.artifact_store import LocalTrainingArtifactStore

class DummyExtractionService:
    def __init__(self, expected_examples: list[TrainingExample]):
        self.expected_examples = expected_examples
        self.called_with = None
        
    def get_training_examples(self, dataset_version_id: uuid.UUID) -> list[TrainingExample]:
        self.called_with = dataset_version_id
        return self.expected_examples

def test_export_service_integration(tmp_path):
    # Setup artifact store securely pointing to testing tmp footprint
    store = LocalTrainingArtifactStore(str(tmp_path))
    
    dv_id = uuid.uuid4()
    
    # 1. Provide deterministic examples
    examples = [
        TrainingExample(
            dataset_version_id=dv_id,
            task_id=uuid.uuid4(),
            task_name="t1",
            prompt="p1",
            canonical_answer="a1",
            metadata={"m": "v1"}
        ),
        TrainingExample(
            dataset_version_id=dv_id,
            task_id=uuid.uuid4(),
            task_name="t2",
            prompt="p2",
            canonical_answer="a2",
            metadata={"m": "v2"}
        )
    ]
    
    extractor = DummyExtractionService(examples)
    service = DatasetExportService(
        extraction_service=extractor,
        artifact_store=store
    )
    
    # 2. Invoke export smoothly parsing native boundaries
    logic_uri = service.export_dataset(dv_id, "jsonl")
    
    assert logic_uri.startswith("artifact://datasets/")
    assert str(dv_id) in logic_uri
    assert logic_uri.endswith(".jsonl")
    
    # 3. Resolve path exactly natively
    physical_path = store.resolve_uri(logic_uri)
    assert str(tmp_path) in physical_path
    
    # 4. Check outputs mapping cleanly properly securely natively
    with open(physical_path, encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 2
    
    parsed_1 = json.loads(lines[0])
    parsed_2 = json.loads(lines[1])
    
    assert parsed_1["prompt"] == "p1"
    assert parsed_1["metadata"]["m"] == "v1"
    assert parsed_2["prompt"] == "p2"
    assert parsed_2["metadata"]["m"] == "v2"

def test_export_service_empty_dataset_fallback(tmp_path):
    store = LocalTrainingArtifactStore(str(tmp_path))
    dv_id = uuid.uuid4()
    # Explicitly empty outputs elegantly handled by exporter structurally avoiding crashes
    extractor = DummyExtractionService([])
    service = DatasetExportService(extraction_service=extractor, artifact_store=store)
    
    logic_uri = service.export_dataset(dv_id, "jsonl")
    physical_path = store.resolve_uri(logic_uri)
    
    with open(physical_path, "rb") as f:
        content = f.read()
    
    assert content == b""  # Empty cleanly 

def test_unsupported_export_format():
    store = LocalTrainingArtifactStore("/tmp/void")
    extractor = DummyExtractionService([])
    service = DatasetExportService(extraction_service=extractor, artifact_store=store)
    
    with pytest.raises(ValueError, match="Unsupported export format"):
        service.export_dataset(uuid.uuid4(), "csv")
