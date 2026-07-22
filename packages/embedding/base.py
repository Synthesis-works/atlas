from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embeds a single text string."""
        pass

    @abstractmethod
    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embeds multiple text strings."""
        pass
