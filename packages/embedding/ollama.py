import httpx
from typing import List
from .base import BaseEmbeddingProvider

class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str = "nomic-embed-text:latest", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def embed(self, text: str) -> List[float]:
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text}
            )
            response.raise_for_status()
            return response.json()["embedding"]

    def embed_many(self, texts: List[str]) -> List[List[float]]:
        # Process sequentially. Can be parallelized later if needed.
        return [self.embed(t) for t in texts]
