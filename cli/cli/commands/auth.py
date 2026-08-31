"""auth commands — whoami, login, logout.

Implements:
  atlas whoami          (human-readable output)
  atlas whoami --json   (JSON output)
  atlas whoami --quiet  (no output, exit code only)
  atlas login           (persist credentials for future commands)
  atlas login --email <email> --password-stdin
  atlas logout
"""

from __future__ import annotations

import sys

import click

from cli.app import Context, _pass_context
from cli.client import build_client
from cli.config import AtlasConfig, clear_saved_token, save_profile
from cli.errors import ExitCode
from cli.output.errors import error_exit
from cli.output.json import render_json, render_json_error
from cli.output.table import render_kv


@click.command(name="whoami")
@_pass_context
def whoami_cmd(ctx: Context) -> None:
    """Show the currently authenticated user.

    Calls GET /api/v1/auth/me through the SDK.

    Examples:

      atlas whoami

      atlas whoami --output json
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if not cfg.token:
        msg = "Not authenticated — run `atlas login` or set ATLAS_TOKEN."
        if output_mode == "json":
            render_json_error(status=401, code="UNAUTHORIZED", message=msg)
        else:
            click.echo(f"error: {msg}", err=True)
        sys.exit(ExitCode.AUTH_REQUIRED)

    try:
        with build_client(cfg) as client:
            user = client.whoami()
    except Exception as exc:
        error_exit(exc, output_mode)

    if output_mode == "json":
        render_json(user.model_dump(mode="json"))
    elif output_mode == "quiet":
        pass
    else:
        rows: list[tuple[str, str]] = [
            ("Email", user.email),
            ("Name", user.full_name),
            ("User ID", str(user.id)),
            ("Organization", str(user.org_id) if user.org_id else "(none)"),
            ("Active", "yes" if user.is_active else "no"),
            ("Verified", "yes" if user.is_verified else "no"),
        ]
        render_kv(rows, title="Atlas User")


@click.command(name="login")
@click.option("--email", default=None, help="Account email address.")
@click.option(
    "--password-stdin",
    is_flag=True,
    default=False,
    help="Read the password from standard input.",
)
@_pass_context
def login_cmd(ctx: Context, email: str | None, password_stdin: bool) -> None:
    """Authenticate and save credentials for future commands.

    The access token is persisted in the current user's profile and is
    never printed.  The active base URL is saved alongside it.

    Examples:

      atlas login

      atlas login --email demo@atlas.val --password-stdin
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    if not email:
        email = click.prompt("Email", type=str)

    if password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            msg = "No password received on stdin."
            if output_mode == "json":
                render_json_error(status=422, code="VALIDATION_ERROR", message=msg)
            else:
                click.echo(f"error: {msg}", err=True)
            sys.exit(ExitCode.VALIDATION)
    else:
        password = click.prompt("Password", hide_input=True)

    try:
        with build_client(cfg) as client:
            token = client.login(email=email, password=password).access_token
    except Exception as exc:
        error_exit(exc, output_mode)

    save_profile(token=token, base_url=cfg.base_url, profile=cfg.profile)

    if output_mode == "json":
        render_json({
            "success": True,
            "email": email,
            "base_url": cfg.base_url,
            "profile": cfg.profile,
        })
    elif output_mode == "quiet":
        pass
    else:
        click.echo(f"Logged in as {email}")


@click.command(name="logout")
@_pass_context
def logout_cmd(ctx: Context) -> None:
    """Clear stored credentials for this profile.

    Does not contact the backend and succeeds even if nothing is stored.

    Examples:

      atlas logout
    """
    cfg: AtlasConfig = ctx.config
    output_mode = cfg.effective_output()

    clear_saved_token(profile=cfg.profile)

    if output_mode == "json":
        render_json({"success": True, "logged_out": True, "profile": cfg.profile})
    elif output_mode == "quiet":
        pass
    else:
        click.echo("Logged out")
