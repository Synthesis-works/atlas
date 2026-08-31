from .base import BaseModelAdapter
from .mock import MockModelAdapter
from .real import RealModelAdapter
from .registry import list_models
from apps.backend.schemas.models import ModelRead


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

    @staticmethod
    def get_available_models() -> list[ModelRead]:
        """Return the authoritative execution-target model catalog.

        Delegates to :func:`apps.backend.adapters.registry.list_models`, which
        shares the exact provider client table (including per-provider
        ``config/providers.json`` overrides) that ``RealModelAdapter`` uses at
        execution time — so the catalog, the resolver, and runtime
        availability cannot diverge.
        """
        return list_models()
