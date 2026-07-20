from .base import BaseModelAdapter
from .mock import MockModelAdapter

class AdapterFactory:
    @staticmethod
    def get_adapter(target_model: str) -> BaseModelAdapter:
        # In the future, parse target_model to return OpenAIAdapter, etc.
        # For Slice 8, we only support mock adapter.
        return MockModelAdapter()
