"""Tests for output renderers — JSON, table, quiet."""

from __future__ import annotations

import io
import json

from cli.output.json import render_json, render_json_error
from cli.output.quiet import render_quiet
from cli.output.table import render_kv, render_message, render_table


def test_render_json_to_file() -> None:
    buf = io.StringIO()
    render_json({"status": "ok", "version": "1.0"}, file=buf)
    raw = buf.getvalue()
    parsed = json.loads(raw)
    assert parsed == {"status": "ok", "version": "1.0"}
    assert raw.endswith("\n")


def test_render_json_list() -> None:
    buf = io.StringIO()
    render_json([{"id": 1}, {"id": 2}], file=buf)
    parsed = json.loads(buf.getvalue())
    assert parsed == [{"id": 1}, {"id": 2}]


def test_render_json_preserves_field_order() -> None:
    buf = io.StringIO()
    render_json({"z": 1, "a": 2, "m": 3}, file=buf)
    parsed = json.loads(buf.getvalue())
    assert list(parsed.keys()) == ["z", "a", "m"]


def test_render_json_error() -> None:
    buf = io.StringIO()
    # Monkeypatch sys.stderr for this test.
    import sys

    old = sys.stderr
    sys.stderr = buf
    try:
        render_json_error(status=401, code="UNAUTHORIZED", message="bad token")
    finally:
        sys.stderr = old
    parsed = json.loads(buf.getvalue())
    assert parsed["error"]["status"] == 401
    assert parsed["error"]["code"] == "UNAUTHORIZED"
    assert "bad token" in parsed["error"]["message"]


def test_render_json_error_with_details() -> None:
    buf = io.StringIO()
    import sys

    old = sys.stderr
    sys.stderr = buf
    try:
        render_json_error(
            status=422,
            code="VALIDATION_ERROR",
            message="invalid input",
            details={"field": "email"},
        )
    finally:
        sys.stderr = old
    parsed = json.loads(buf.getvalue())
    assert parsed["error"]["details"] == {"field": "email"}


def test_render_kv() -> None:
    buf = io.StringIO()
    render_kv([("Name", "Alice"), ("Email", "a@b.com")], title="User", file=buf)
    out = buf.getvalue()
    assert "User" in out
    assert "Alice" in out
    assert "a@b.com" in out


def test_render_kv_empty() -> None:
    buf = io.StringIO()
    render_kv([], file=buf)
    assert "(no data)" in buf.getvalue()


def test_render_table() -> None:
    buf = io.StringIO()
    render_table(
        ["ID", "Name"],
        [["1", "Alpha"], ["2", "Beta"]],
        title="Items",
        file=buf,
    )
    out = buf.getvalue()
    assert "Items" in out
    assert "Alpha" in out
    assert "Beta" in out
    assert "ID" in out
    assert "Name" in out


def test_render_table_empty() -> None:
    buf = io.StringIO()
    render_table(["ID"], [], file=buf)
    assert "(empty)" in buf.getvalue()


def test_render_message() -> None:
    buf = io.StringIO()
    render_message("hello", file=buf)
    assert buf.getvalue().strip() == "hello"


def test_render_quiet_no_output() -> None:
    buf = io.StringIO()
    render_quiet({"key": "value"}, file=buf)
    assert buf.getvalue() == ""
