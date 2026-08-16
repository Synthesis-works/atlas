import json
from typing import Any, Iterable, cast

from pydantic import BaseModel

from .base import Exporter, ExportResult


class JSONExporter(Exporter):
    def export(self, data: Iterable[Any] | dict[str, Any] | BaseModel) -> ExportResult:
        if isinstance(data, BaseModel):
            content = json.dumps(data.model_dump(mode="json"), indent=2).encode("utf-8")
        elif isinstance(data, dict):
            content = json.dumps(data, indent=2).encode("utf-8")
        else:
            items: list[dict[str, Any]] = []
            for item in cast(Iterable[Any], data):
                if isinstance(item, BaseModel):
                    items.append(item.model_dump(mode="json"))
                else:
                    items.append(cast(dict[str, Any], item))
            content = json.dumps(items, indent=2).encode("utf-8")

        return ExportResult(
            content=content,
            mime_type="application/json",
            filename_extension="json",
        )
