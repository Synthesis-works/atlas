import json
import os
from typing import Any


class ExperimentRegistry:
    def __init__(self, registry_file: str = "results/experiments/registry.json"):
        self.registry_file = registry_file
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, encoding="utf-8") as f:
                    return json.load(f)  # type: ignore
            except json.JSONDecodeError:
                return []
        return []

    def _save(self, data: list[dict[str, Any]]):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register(self, exp_id: str, config: dict[str, Any], metrics: dict[str, Any]):
        registry = self._load()

        # Check if already exists
        for entry in registry:
            if entry.get("id") == exp_id:
                # Update it
                entry.update({"config": config, "metrics": metrics})
                self._save(registry)
                return

        # Append new
        entry = {
            "id": exp_id,
            "parent": config.get("parent_experiment"),
            "change": config.get("lineage_change"),
            "reason": config.get("lineage_reason"),
            "dataset": config.get("dataset"),
            "model": config.get("model"),
            "prompt_version": config.get("prompt_version"),
            "seed": config.get("seed"),
            "atlas_version": config.get("atlas_version"),
            "pass_at_1": metrics.get("pass_at_1"),
            "total_tasks": metrics.get("total_tasks"),
            "config": config,
            "metrics": metrics,
        }

        registry.append(entry)
        self._save(registry)

    def get_all(self) -> list[dict[str, Any]]:
        return self._load()
