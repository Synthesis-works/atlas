from .base import BaseNormalizer


class NoopNormalizer(BaseNormalizer):
    def normalize(self, text: str) -> str:
        return text.strip()
