from .base import Exporter
from .csv_exporter import CSVExporter
from .json_exporter import JSONExporter


class ExporterRegistry:
    def __init__(self) -> None:
        self._exporters: dict[str, Exporter] = {}

    def register(self, format_key: str, exporter: Exporter) -> None:
        self._exporters[format_key.lower()] = exporter

    def get_exporter(self, format_key: str) -> Exporter | None:
        return self._exporters.get(format_key.lower())


# Default registry singleton
registry = ExporterRegistry()
registry.register("json", JSONExporter())
registry.register("csv", CSVExporter())


def get_exporter(format_key: str) -> Exporter | None:
    return registry.get_exporter(format_key)
