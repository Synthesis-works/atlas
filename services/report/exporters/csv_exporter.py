import csv
import io
from typing import Any, Iterable

from pydantic import BaseModel

from .base import Exporter, ExportResult


class CSVExporter(Exporter):
    def export(self, data: Iterable[Any]) -> ExportResult:
        items = []
        for item in data:
            if isinstance(item, BaseModel):
                items.append(item.model_dump(mode="json"))
            else:
                items.append(item)

        output = io.StringIO()
        if not items:
            return ExportResult(
                content=b"",
                mime_type="text/csv",
                filename_extension="csv",
            )

        fieldnames = list(items[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for item in items:
            flat_item = {}
            for k, v in item.items():
                if isinstance(v, (dict, list)):
                    flat_item[k] = str(v)
                else:
                    flat_item[k] = v
            writer.writerow(flat_item)

        return ExportResult(
            content=output.getvalue().encode("utf-8"),
            mime_type="text/csv",
            filename_extension="csv",
        )
