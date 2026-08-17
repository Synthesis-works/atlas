import json
from packages.datasets.models import TrainingExample
from .base import DatasetExporter, DatasetExportResult


class JSONLDatasetExporter(DatasetExporter):
    """
    Exports a list of TrainingExamples into strict, deterministic JSONL format.
    Every row is serialized exactly, and ordering matches the input array to preserve sequence.
    """

    def export(self, examples: list[TrainingExample]) -> DatasetExportResult:
        lines = []
        for ex in examples:
            # model_dump(mode="json") automatically handles UUID->str and dict schemas natively
            dump_val = ex.model_dump(mode="json")
            # strict determinism enforcing sorting across dictionary outputs avoiding diff inflation natively
            line_str = json.dumps(
                dump_val, separators=(",", ":"), sort_keys=True, ensure_ascii=False
            )
            lines.append(line_str)

        # Ensure trailing newline on the payload for proper linux tail configurations
        content_str = "\n".join(lines) + "\n" if lines else ""
        content = content_str.encode("utf-8")

        return DatasetExportResult(
            content=content, mime_type="application/jsonlines", filename_extension="jsonl"
        )
