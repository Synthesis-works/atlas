"""Offline JSON Schema emission for ``--json-schema`` (Slice 6).

Schema documents are resolved from the SDK pydantic models at parse time —
never from the backend — so the flag behaves like ``--help``: deterministic,
machine-readable, and available while the backend is offline.  Only commands
whose JSON output is a faithful pydantic model dump expose the flag.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from cli.output.json import render_json

_JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def _item_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema without the outer ``$schema`` key."""
    return model.model_json_schema()


class SchemaDocument(dict[str, Any]):
    """A complete JSON Schema document for a single model's output.

    ``model_json_schema()`` already expresses nested structures through
    ``$defs``/``$ref``; this adds the dialect key so the output is
    self-describing.
    """

    def __init__(self, model: type[BaseModel]) -> None:
        super().__init__({"$schema": _JSON_SCHEMA_DIALECT, **_item_schema(model)})


class ArraySchemaDocument(dict[str, Any]):
    """JSON Schema for a bare ``list[Model]`` output (e.g. leaderboard history)."""

    def __init__(self, model: type[BaseModel]) -> None:
        super().__init__(
            {
                "$schema": _JSON_SCHEMA_DIALECT,
                "type": "array",
                "items": _item_schema(model),
            }
        )


def emit_json_schema(
    model: type[BaseModel], *, output_mode: str, array: bool = False
) -> bool:
    """Emit the schema document and report the flag was handled.

    In ``quiet`` mode the flag is a no-op (no stdout, exit 0) — ``--quiet``
    semantics stay unchanged.  Otherwise the schema is rendered with the
    standard JSON renderer.
    """
    document: dict[str, Any] = ArraySchemaDocument(model) if array else SchemaDocument(model)
    if output_mode != "quiet":
        render_json(document)
    return True
