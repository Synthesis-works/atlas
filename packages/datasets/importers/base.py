import hashlib
from abc import ABC, abstractmethod
from typing import List, Any
from ..models import DatasetPack, DatasetManifest, ImportStats
from ..mapper import BaseMapper
from packages.benchmark.models.task import Task

class BaseImporter(ABC):
    def __init__(self, mapper: BaseMapper):
        self.mapper = mapper

    @abstractmethod
    def fetch_dataset(self) -> List[Any]:
        """Downloads or loads the raw dataset records."""
        pass

    @abstractmethod
    def get_manifest(self) -> DatasetManifest:
        """Returns the manifest for this dataset."""
        pass

    def compute_checksum(self, tasks: List[Task]) -> str:
        content = "".join([f"{t.task_id}:{t.input}" for t in tasks])
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def import_pack(self) -> DatasetPack:
        raw_records = self.fetch_dataset()
        tasks = []
        stats = ImportStats(total=len(raw_records))
        seen_ids = set()
        manifest = self.get_manifest()

        for record in raw_records:
            try:
                task = self.mapper.map(record)
                if task.task_id in seen_ids:
                    stats.duplicates += 1
                else:
                    seen_ids.add(task.task_id)
                    tasks.append(task)
                    stats.valid += 1
                    
                    lang = manifest.language
                    stats.languages[lang] = stats.languages.get(lang, 0) + 1
            except Exception as e:
                print(f"Error mapping record: {e}")
                stats.missing_metadata += 1

        stats.checksum = self.compute_checksum(tasks)
        return DatasetPack(manifest=manifest, tasks=tasks, stats=stats)
