"""JSON output renderer — exactly one JSON document on stdout (§9.2)."""

from __future__ import annotations

import json
import sys
from typing import Any


def render_json(data: Any, *, file: Any | None = None) -> None:
    """Serialize *data* as JSON to stdout (or *file*).

    Rules (§9.2):
      - Exactly one JSON document on stdout; nothing else.
      - Warnings/errors go to stderr.
      - Stable field order follows DTO declaration order.
    """
    target = file or sys.stdout
    json.dump(data, target, indent=2, ensure_ascii=False, sort_keys=False)
    target.write("\n")


def render_json_error(
    *,
    status: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> None:
    """Write a structured error document to stderr in JSON mode (§10)."""
    error_obj: dict[str, Any] = {
        "error": {
            "status": status,
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        error_obj["error"]["details"] = details
    json.dump(error_obj, sys.stderr, indent=2, ensure_ascii=False)
    sys.stderr.write("\n")
