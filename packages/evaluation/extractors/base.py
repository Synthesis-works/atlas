from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, response_text: str) -> str:
        """Extracts the relevant part of the response."""
        pass
