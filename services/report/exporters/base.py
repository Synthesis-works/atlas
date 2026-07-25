import abc
import csv
import io
import json
from typing import Any


class Exporter(abc.ABC):
    @abc.abstractmethod
    def export(self, data: Any) -> bytes:
        pass


class JSONExporter(Exporter):
    def export(self, data: Any) -> bytes:
        # Assuming data is a Pydantic model or dict
        if hasattr(data, "model_dump"):
            export_data = data.model_dump()
        else:
            export_data = data
        return json.dumps(export_data, default=str).encode("utf-8")


class CSVExporter(Exporter):
    def export(self, data: Any) -> bytes:
        # Very naive implementation assuming data is a list of dicts
        if not data:
            return b""

        if hasattr(data, "model_dump"):
            export_data = data.model_dump()
        else:
            export_data = data

        if not isinstance(export_data, list) or not isinstance(export_data[0], dict):
            # Fallback for non-tabular data
            return json.dumps(export_data, default=str).encode("utf-8")

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=export_data[0].keys())
        writer.writeheader()
        for row in export_data:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")
