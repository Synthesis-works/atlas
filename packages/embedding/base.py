from abc import ABC, abstractmethod
from typing import List

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """Embeds a single text string."""
        pass

    @abstractmethod
    def embed_many(self, texts: List[str]) -> List[List[float]]:
        """Embeds multiple text strings."""
        pass
