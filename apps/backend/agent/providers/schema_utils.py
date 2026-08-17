"""
Shared schema utilities for Atlas Agent provider adapters.

The Atlas ToolRegistry produces Gemini-style functionDeclaration schemas
with UPPERCASE type names (OBJECT, STRING, INTEGER, ARRAY, BOOLEAN).

OpenAI-compatible APIs (Groq, Mistral, xAI) require standard JSON Schema
casing with lowercase type names (object, string, integer, array, boolean).

This module provides a single canonical normalizer so each adapter
does not need its own conversion logic.

The normalizer never mutates the original Gemini schema in-place: every
conversion produces a brand-new dict tree, so the canonical Gemini schema
remains untouched for the Gemini provider.
"""

from typing import Any
import json

# Canonical Gemini-style UPPERCASE types -> OpenAI/JSON Schema lowercase.
_TYPE_MAP: dict[str, str] = {
    "OBJECT": "object",
    "STRING": "string",
    "INTEGER": "integer",
    "NUMBER": "number",
    "BOOLEAN": "boolean",
    "ARRAY": "array",
    "NULL": "null",
}

# Keys whose values are a single nested schema (recursed as one object).
_SINGLE_SCHEMA_KEYS = ("items", "additionalProperties", "not")

# Keys whose values are a list of schemas (recursed element-by-element).
_LIST_SCHEMA_KEYS = ("anyOf", "oneOf", "allOf", "prefixItems")


def _normalize_schema(schema: Any) -> Any:
    """
    Recursively lowercase all JSON Schema type names.

    Accepts either a dict schema or a list of schemas. Returns a new,
    fully-normalized structure without mutating the input.
    """
    if isinstance(schema, dict):
        return _normalize_schema_object(schema)
    if isinstance(schema, list):
        return [_normalize_schema(item) for item in schema]
    return schema


def _normalize_schema_object(schema: dict[str, Any]) -> dict[str, Any]:
    """Recursively normalize a single JSON Schema object."""
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            result[key] = _normalize_type(value)
        elif key in _SINGLE_SCHEMA_KEYS and isinstance(value, dict):
            result[key] = _normalize_schema_object(value)
        elif key in _LIST_SCHEMA_KEYS and isinstance(value, list):
            result[key] = [
                _normalize_schema_object(item) for item in value if isinstance(item, dict)
            ]
        elif key == "properties" and isinstance(value, dict):
            result[key] = {
                prop_name: _normalize_schema_object(prop_spec)
                for prop_name, prop_spec in value.items()
                if isinstance(prop_spec, dict)
            }
        elif key == "patternProperties" and isinstance(value, dict):
            result[key] = {
                pattern: _normalize_schema_object(prop_spec)
                for pattern, prop_spec in value.items()
                if isinstance(prop_spec, dict)
            }
        elif key == "required" and isinstance(value, list):
            # `required` is a plain list of string names — never touch its contents.
            result[key] = list(value)
        elif key == "enum" and isinstance(value, list):
            # `enum` holds literal values — leave untouched.
            result[key] = list(value)
        elif isinstance(value, (dict, list)):
            # Unknown nested containers: recurse defensively.
            result[key] = _normalize_schema(value)
        else:
            result[key] = value
    return result


def _normalize_type(raw: str) -> str:
    """Map an UPPERCASE Gemini type to lowercase JSON Schema, with pass-through for already-lowercase input."""
    stripped = raw.strip()
    mapped = _TYPE_MAP.get(stripped)
    if mapped:
        return mapped
    return stripped.lower()


def normalize_tool_schema_for_openai(gemini_schema: dict[str, Any]) -> dict[str, Any]:
    """
    Converts a Gemini functionDeclaration schema into an OpenAI-compatible
    function tool spec.

    Input (Gemini format):
        {
            "name": "create_benchmark",
            "description": "...",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "..."},
                    "count": {"type": "INTEGER", "description": "..."},
                    "tags": {"type": "ARRAY", "items": {"type": "STRING"}, ...}
                },
                "required": ["name"]
            }
        }

    Output (OpenAI format):
        {
            "type": "function",
            "function": {
                "name": "create_benchmark",
                "description": "...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "..."},
                        "count": {"type": "integer", "description": "..."},
                        "tags": {"type": "array", "items": {"type": "string"}, ...}
                    },
                    "required": ["name"]
                }
            }
        }
    """
    parameters = gemini_schema.get("parameters", {"type": "object", "properties": {}})
    normalized_params = _normalize_schema_object(parameters)

    return {
        "type": "function",
        "function": {
            "name": gemini_schema.get("name", ""),
            "description": gemini_schema.get("description", ""),
            "parameters": normalized_params,
        },
    }


def normalize_tools_for_openai(available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Batch-normalize a list of Gemini functionDeclaration schemas
    into OpenAI-compatible tool specs.
    """
    return [normalize_tool_schema_for_openai(t) for t in available_tools]


def extract_json_object(text: str) -> dict[str, Any] | None:
    """
    Extract the first balanced JSON object from free-text provider output.

    Provider models sometimes wrap tool calls in prose or markdown fences
    instead of returning native ``tool_calls``. This helper scans the text
    for a balanced ``{...}`` object (handling nested braces) and parses it.

    Returns the parsed dict, or None if no valid JSON object was found.
    """
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    pass
    return None
