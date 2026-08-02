from .base import BaseNormalizer


class LowercaseNormalizer(BaseNormalizer):
    def normalize(self, text: str) -> str:
        return text.strip().lower()
