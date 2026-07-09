import re
from .base import BaseExtractor

class CodeBlockExtractor(BaseExtractor):
    """Extracts content inside markdown code blocks (```python ... ```)"""
    def extract(self, response_text: str) -> str:
        pattern = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.DOTALL)
        match = pattern.search(response_text)
        if match:
            return match.group(1).strip()
        return response_text
