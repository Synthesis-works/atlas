"""health commands — health summary (Phase 1).

Implements:
  atlas health          (human-readable)
  atlas health --json   (JSON output)
  atlas health --quiet  (exit code only)
"""

from __future__ import annotations

import contextlib
import sys
from typing import Any

import click
from atlas_sdk.errors import ApiError, NetworkError

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig
from cli.errors import ExitCode
from cli.output.errors import error_exit
from cli.output.json import render_json
from cli.output.table import render_kv


@click.command(name="health")
@_pass_context
def health_cmd(ctx: Context) -> None:
    """Check Atlas API health.

    Calls GET /health, GET /api/v1/system/health/live,
    and GET /api/v1/system/health/ready through the SDK.

    Examples:

      atlas health

      atlas health --output json --quiet
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    try:
        with build_client(cfg) as client:
            health_data = None
            with contextlib.suppress(ApiError, NetworkError):
                health_data = client.health_summary()

            live = None
            with contextlib.suppress(ApiError, NetworkError):
                live = client.system_live()

            ready = None
            with contextlib.suppress(ApiError, NetworkError):
                ready = client.system_ready()
    except Exception as exc:
        error_exit(exc, output_mode)

    all_ok = (
        health_data is not None
        and live is not None
        and ready is not None
    )

    if output_mode == "json":
        result: dict[str, Any] = {
            "api": health_data.model_dump(mode="json") if health_data else None,
            "liveness": live.model_dump(mode="json") if live else None,
            "readiness": ready.model_dump(mode="json") if ready else None,
            "overall": "healthy" if all_ok else "degraded",
        }
        render_json(result)
        if not all_ok:
            sys.exit(ExitCode.UNSPECIFIED)
    elif output_mode == "quiet":
        if not all_ok:
            sys.exit(ExitCode.UNSPECIFIED)
    else:
        rows: list[tuple[str, str]] = []
        if health_data:
            rows.append(("API Status", health_data.status))
            rows.append(("API Version", health_data.version))
        else:
            rows.append(("API Status", "unreachable"))

        if live:
            rows.append(("Liveness", live.status))
        else:
            rows.append(("Liveness", "unreachable"))

        if ready:
            rows.append(("Readiness", ready.status))
            if ready.checks:
                for check_name, check_val in ready.checks.items():
                    rows.append((f"  {check_name}", str(check_val)))
        else:
            rows.append(("Readiness", "unreachable"))

        rows.append(("Overall", "healthy" if all_ok else "degraded"))
        render_kv(rows, title="Atlas Health")
        if not all_ok:
            sys.exit(ExitCode.UNSPECIFIED)
