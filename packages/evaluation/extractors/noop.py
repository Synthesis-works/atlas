from .base import BaseExtractor

class NoopExtractor(BaseExtractor):
    def extract(self, response_text: str) -> str:
        return response_text
