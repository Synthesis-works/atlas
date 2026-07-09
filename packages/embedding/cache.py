import os
import json
import hashlib
from typing import List
from .base import BaseEmbeddingProvider

class CachedEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, provider: BaseEmbeddingProvider, cache_dir: str = "cache/embeddings"):
        self.provider = provider
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, text: str) -> str:
        # Hash the text to create a unique cache filename
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.json")

    def embed(self, text: str) -> List[float]:
        path = self._get_cache_path(text)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
                
        # Cache miss, fetch from provider
        vector = self.provider.embed(text)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(vector, f)
            
        return vector

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]
