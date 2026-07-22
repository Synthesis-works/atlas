from .base import BaseNormalizer


class WhitespaceNormalizer(BaseNormalizer):
    def normalize(self, text: str) -> str:
        return " ".join(text.split())
