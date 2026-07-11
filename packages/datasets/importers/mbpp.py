import os
import json
from typing import Any, List
from .base import BaseImporter
from ..mapper import BaseMapper
from ..models import DatasetManifest
from packages.benchmark.models.task import Task, EvaluationConfig

class MBPPMapper(BaseMapper):
    def map(self, raw_record: Any) -> Task:
        text = raw_record["text"]
        tests = raw_record.get("test_list", [])
        
        example_str = ""
        if tests:
            example_str = f"\n\nExample:\n{tests[0]}"
            
        return Task(
            task_id=f"mbpp-{raw_record['task_id']}",
            title=f"MBPP {raw_record['task_id']}",
            description=text,
            input=text + example_str,
            expected_output=raw_record["code"],
            hidden_tests=raw_record.get("test_list", []),
            evaluation=EvaluationConfig(
                extractor="code_block",
                normalizer="noop",
                judge="exact_match",
                metrics=["accuracy"]
            ),
            metadata={"test_setup_code": raw_record.get("test_setup_code", "")}
        )

class MBPPImporter(BaseImporter):
    DATASET_URL = "https://raw.githubusercontent.com/google-research/google-research/master/mbpp/mbpp.jsonl"
    
    def __init__(self):
        super().__init__(mapper=MBPPMapper())
        
    def get_manifest(self) -> DatasetManifest:
        return DatasetManifest(
            id="mbpp",
            name="Mostly Basic Python Problems",
            version="1.0",
            source="Google Research",
            license="CC-BY-4.0",
            citation="Program Synthesis with Large Language Models (Austin et al. 2021)",
            language="python",
            evaluation="execution",
            metric="pass@1",
            tasks=974,
            tags=["coding", "python", "generation", "basic"]
        )
        
    def fetch_dataset(self) -> List[Any]:
        file_path = os.path.join("datasets", "mbpp", "mbpp.jsonl")
        records = []
        with open(file_path, 'rt', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
