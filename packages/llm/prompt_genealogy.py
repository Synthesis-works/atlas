import json
import os
from typing import Dict, Any, List

class PromptGenealogy:
    def __init__(self, prompts_dir: str = "prompts", benchmark_pack: str = None):
        self.prompts_dir = prompts_dir
        
        if benchmark_pack:
            self.metadata_path = os.path.join(self.prompts_dir, benchmark_pack, "metadata.json")
        else:
            self.metadata_path = os.path.join(self.prompts_dir, "metadata.json")
            
        self._load()
        
    def _load(self):
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
            
    def get_prompt_info(self, version: str) -> Dict[str, Any]:
        """
        Returns info about a prompt variant: family, changes, previous_variant.
        """
        for family, variants in self.metadata.items():
            if version in variants:
                info = variants[version].copy()
                info["family"] = family
                return info
        return {"family": "Unknown"}
