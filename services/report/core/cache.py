from typing import Any, Optional
import abc

class ReportCache(abc.ABC):
    @abc.abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass

    @abc.abstractmethod
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        pass

class NoopReportCache(ReportCache):
    """
    A no-op cache implementation.
    Allows controllers and services to use cache semantics without
    needing a real caching backend like Redis immediately.
    """
    def get(self, key: str) -> Optional[Any]:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        pass
