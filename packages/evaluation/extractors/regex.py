import re
from .base import BaseExtractor

class RegexExtractor(BaseExtractor):
    def __init__(self, pattern: str, group: int = 1):
        self.pattern = re.compile(pattern)
        self.group = group

    def extract(self, response_text: str) -> str:
        match = self.pattern.search(response_text)
        if match:
            return match.group(self.group)
        return response_text
