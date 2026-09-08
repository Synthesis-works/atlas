"""Tests for per-platform agent brain setup guidance.

Covers: the exact per-shell commands rendered for Gemini and Groq, the
missing-key message shown at exit 10, that only placeholder values are ever
rendered (no real keys can leak into output), and that the app gate and
``--provider`` path surface the improved guidance.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cli.agent.setup import (
    PROVIDER_ENV_VAR,
    PROVIDER_PLACEHOLDER,
    missing_key_message,
    setup_command,
    setup_commands,
)
from cli.app import main
from cli.errors import ExitCode


class TestSetupCommands:
    def test_provider_metadata_is_complete(self) -> None:
        assert set(PROVIDER_ENV_VAR) == {"gemini", "groq"}
        assert set(PROVIDER_PLACEHOLDER) == {"gemini", "groq"}
        assert PROVIDER_ENV_VAR["gemini"] == "GEMINI_API_KEY"
        assert PROVIDER_ENV_VAR["groq"] == "GROQ_API_KEY"

    def test_powershell_command_format(self) -> None:
        assert setup_command("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY", "powershell") == (
            '$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'
        )
        assert setup_command("GROQ_API_KEY", "YOUR_GROQ_API_KEY", "powershell") == (
            '$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"'
        )

    def test_shell_export_format(self) -> None:
        assert setup_command("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY", "shell") == (
            'export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"'
        )
        assert setup_command("GROQ_API_KEY", "YOUR_GROQ_API_KEY", "shell") == (
            'export GROQ_API_KEY="YOUR_GROQ_API_KEY"'
        )

    def test_colab_format(self) -> None:
        assert setup_command("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY", "colab") == (
            "%env GEMINI_API_KEY=YOUR_GEMINI_API_KEY"
        )
        assert setup_command("GROQ_API_KEY", "YOUR_GROQ_API_KEY", "colab") == (
            "%env GROQ_API_KEY=YOUR_GROQ_API_KEY"
        )

    def test_setup_commands_covers_all_shells_per_provider(self) -> None:
        for provider in ("gemini", "groq"):
            labels = [label for label, _cmd in setup_commands(provider)]
            assert labels == [
                "Windows PowerShell",
                "macOS / Linux / Git Bash",
                "Google Colab",
            ]


class TestMissingKeyMessage:
    def test_keeps_required_substrings(self) -> None:
        from cli.app import _agent_unavailable_message

        message = _agent_unavailable_message()
        assert "Atlas agent brain unavailable" in message
        assert "GROQ_API_KEY" in message
        assert "GEMINI_API_KEY" in message
        assert message == missing_key_message()

    def test_includes_powershell_and_export_commands(self) -> None:
        message = missing_key_message()
        assert '$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"' in message
        assert 'export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"' in message
        assert "%env GEMINI_API_KEY=YOUR_GEMINI_API_KEY" in message

    def test_includes_groq_commands(self) -> None:
        message = missing_key_message()
        assert '$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"' in message
        assert 'export GROQ_API_KEY="YOUR_GROQ_API_KEY"' in message
        assert "%env GROQ_API_KEY=YOUR_GROQ_API_KEY" in message

    def test_explains_bash_vs_powershell(self) -> None:
        assert "export KEY=" in missing_key_message()
        assert "$env:KEY=" in missing_key_message()

    def test_only_placeholders_ever_rendered(self) -> None:
        """The setup output must never carry a concrete key value."""
        rendered = [cmd for _label, cmd in setup_commands("gemini")] + [
            cmd for _label, cmd in setup_commands("groq")
        ]
        values = {cmd.split("=", 1)[1].strip('"') for cmd in rendered}
        assert values == {"YOUR_GEMINI_API_KEY", "YOUR_GROQ_API_KEY"}
        message = missing_key_message()
        for placeholder in PROVIDER_PLACEHOLDER.values():
            assert placeholder in message


class TestCliSurface:
    def test_agent_without_any_key_exits_10_with_actionable_message(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        result = runner.invoke(main, ["agent", "list benchmarks"])
        assert result.exit_code == ExitCode.AGENT_UNAVAILABLE
        out = result.output
        assert "Atlas agent brain unavailable" in out
        assert '$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"' in out
        assert 'export GROQ_API_KEY="YOUR_GROQ_API_KEY"' in out

    def test_pinned_provider_missing_points_at_its_env_var(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """--provider groq with only a GEMINI key pinned: no fallback, env-var hint."""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        result = runner.invoke(main, ["agent", "--provider", "groq", "hello"])
        assert result.exit_code == ExitCode.UNSPECIFIED
        out = result.output
        assert "not available" in out
        assert "GROQ_API_KEY" in out

    def test_shell_commands_are_well_formed(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sanity guard: commands are well-formed per shell (no stray quotes)."""
        for provider in ("gemini", "groq"):
            for shell in ("powershell", "shell", "colab"):
                cmd = setup_command(
                    PROVIDER_ENV_VAR[provider], PROVIDER_PLACEHOLDER[provider], shell
                )
                assert (cmd.count('"') % 2) == 0  # balanced quotes for quoted forms
                assert ".." not in cmd
