from .base import BaseModelAdapter
from .mock import MockModelAdapter
from .real import RealModelAdapter


class AdapterFactory:
    @staticmethod
    def get_adapter(target_model: str) -> BaseModelAdapter:
        """
        Factory method routing model targets to model adapters.
        Target model 'mock' or 'mocked' selects the MockModelAdapter.
        All real model targets route through RealModelAdapter.
        """
        if not target_model:
            return MockModelAdapter()

        normalized = target_model.strip().lower()
        if normalized in ("mock", "mocked"):
            return MockModelAdapter()

        return RealModelAdapter(target_model=target_model)
