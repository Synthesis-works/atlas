import json
from typing import Any, Iterable

from pydantic import BaseModel

from .base import Exporter, ExportResult


class JSONExporter(Exporter):
    def export(self, data: Iterable[Any]) -> ExportResult:
        items = []
        for item in data:
            if isinstance(item, BaseModel):
                items.append(item.model_dump(mode="json"))
            else:
                items.append(item)

        content = json.dumps(items, indent=2).encode("utf-8")

        return ExportResult(
            content=content,
            mime_type="application/json",
            filename_extension="json",
        )
