import os
from typing import Any

import yaml

from ..exceptions import LoaderError
from ..interfaces.loader import FileLoader


class YAMLLoader(FileLoader):
    """Loads a benchmark definition from a YAML file."""

    def load_file(self, file_path: str) -> dict[str, Any]:
        if not os.path.exists(file_path):
            raise LoaderError(f"File not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise LoaderError(f"Failed to parse YAML file {file_path}: {e}")
        except Exception as e:
            raise LoaderError(f"Error loading {file_path}: {e}")
