"""model commands (Slice 7).

Implements:
  atlas model list                   (human-readable table)
  atlas --output json model list     (JSON output — bare array of ModelRead)
  atlas --quiet model list           (exit code only)
  atlas model list --json-schema     (offline JSON Schema of the array items)

Every ``id`` in the output is a canonical value accepted by
``run submit --target-model``.  ``NOT_CONFIGURED`` means Atlas knows the model
but this deployment lacks the credentials/host to execute it — not that it is
invalid.
"""

from __future__ import annotations

import click
from atlas_sdk import ModelRead

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.schema import emit_json_schema
from cli.output.table import render_table


@click.group(name="model")
def model_group() -> None:
    """Model operations.

    Examples:

      atlas model list

      atlas --output json model list
    """


@model_group.command(name="list")
@click.option(
    "--json-schema",
    is_flag=True,
    default=False,
    help="Print the JSON Schema of this command's JSON output (offline) and exit.",
)
@_pass_context
def list_cmd(ctx: Context, json_schema: bool) -> None:
    """List the execution target models `run submit --target-model` accepts.

    Calls GET /api/v1/models through the SDK.

    Examples:

      atlas model list

      atlas --output json model list

      atlas model list --json-schema
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if json_schema:
        emit_json_schema(ModelRead, output_mode=output_mode, array=True)
        return

    try:
        with build_client(cfg) as client:
            models = client.list_models()
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        items = [m.model_dump(mode="json") for m in models]
        render_json(items)
    elif output_mode == "quiet":
        pass
    else:
        if not models:
            click.echo("  (no models)")
            return
        headers = ["Model", "Provider", "Status", "Test Only"]
        rows = [
            [m.id, m.provider, m.status.value, "yes" if m.is_test_only else "no"]
            for m in models
        ]
        render_table(headers, rows, title="Available Models")
