from abc import ABC, abstractmethod
from typing import Dict, Optional, Any

class TelemetrySink(ABC):
    """
    Vendor-neutral abstraction for recording metrics.
    """
    @abstractmethod
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        pass
    
    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        pass


class NullTelemetrySink(TelemetrySink):
    """
    A sink that ignores all telemetry (useful for testing or when metrics are disabled).
    """
    def record_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
        pass
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        pass
    
    def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        pass

# Prometheus implementation would be deferred or implemented if prometheus_client is installed.
# We will provide a basic implementation if needed.
