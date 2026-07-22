import json
import os
from typing import Any

from ..exceptions import LoaderError
from ..interfaces.loader import FileLoader


class JSONLoader(FileLoader):
    """Loads a benchmark definition from a JSON file."""

    def load_file(self, file_path: str) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise LoaderError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise LoaderError(f"Failed to parse JSON file {file_path}: {e}")
        except Exception as e:
            raise LoaderError(f"Error loading {file_path}: {e}")
