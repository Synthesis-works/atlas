from abc import ABC, abstractmethod

class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, text: str) -> str:
        """Normalizes the extracted text for deterministic judging."""
        pass
