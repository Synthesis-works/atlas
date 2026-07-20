import json
import os
from typing import Dict, Any

class ResearchQuestionTracker:
    def __init__(self, registry_file: str = "research/questions/registry.json"):
        self.registry_file = registry_file
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        
    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}
        
    def _save(self, data: Dict[str, Any]):
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    def add_question(self, rq_id: str, question: str):
        data = self._load()
        if rq_id not in data:
            data[rq_id] = {
                "question": question,
                "experiments": [],
                "findings": [],
                "status": "open"
            }
            self._save(data)
            
    def link_experiment(self, rq_id: str, exp_id: str, note: str = ""):
        data = self._load()
        if rq_id in data:
            if exp_id not in [e["exp_id"] for e in data[rq_id]["experiments"]]:
                data[rq_id]["experiments"].append({
                    "exp_id": exp_id,
                    "note": note
                })
                self._save(data)
                
    def add_finding(self, rq_id: str, finding: str):
        data = self._load()
        if rq_id in data:
            data[rq_id]["findings"].append(finding)
            self._save(data)
