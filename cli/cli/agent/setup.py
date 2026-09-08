"""Per-platform API-key setup guidance for the Atlas agent brain.

The agent refuses to start (exit code 10) when no LLM provider key is
configured.  These helpers render actionable, per-shell setup snippets so a
new user knows exactly how to define ``GROQ_API_KEY`` / ``GEMINI_API_KEY`` in
their own environment: Windows PowerShell, macOS/Linux (or Git Bash), and
Google Colab.

Values rendered are *placeholders only* — a real key is never echoed,
printed, or logged.  The CLI reads keys exclusively via ``os.environ``; this
module never inspects or reports an actual value.
"""

from __future__ import annotations

#: provider id (matches the ``--provider`` choice values) -> env-var name
PROVIDER_ENV_VAR: dict[str, str] = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
}

#: provider id -> placeholder value shown in setup snippets (never a real key)
PROVIDER_PLACEHOLDER: dict[str, str] = {
    "gemini": "YOUR_GEMINI_API_KEY",
    "groq": "YOUR_GROQ_API_KEY",
}

#: (shell id, human label) in display order.  PowerShell first on purpose:
#: the classic footgun is running Bash ``export KEY="..."`` in a Windows
#: PowerShell session, so the correct Windows syntax is what users see first.
_SHELLS: tuple[tuple[str, str], ...] = (
    ("powershell", "Windows PowerShell"),
    ("shell", "macOS / Linux / Git Bash"),
    ("colab", "Google Colab"),
)


def setup_command(env_var: str, placeholder: str, shell: str) -> str:
    """Render the one-line command that defines ``env_var`` in ``shell``.

    ``placeholder`` is the value to substitute with a real key.  A real key
    must never be passed to this function.
    """
    if shell == "powershell":
        return f'$env:{env_var}="{placeholder}"'
    if shell == "colab":
        return f"%env {env_var}={placeholder}"
    return f'export {env_var}="{placeholder}"'


def setup_commands(provider: str) -> list[tuple[str, str]]:
    """Return [(shell label, command), ...] for a provider across all shells."""
    env_var = PROVIDER_ENV_VAR[provider]
    placeholder = PROVIDER_PLACEHOLDER[provider]
    return [(label, setup_command(env_var, placeholder, shell)) for shell, label in _SHELLS]


def missing_key_message() -> str:
    """Friendly, actionable message shown when the agent brain has no key."""
    lines: list[str] = [
        "error: Atlas agent brain unavailable. Set GROQ_API_KEY or GEMINI_API_KEY "
        "to use the Atlas agent.",
        "",
        "The agent runs on an LLM provider API key. Configure one, then retry "
        '`atlas agent "your task"`. The Bash form `export KEY="..."` is for '
        'macOS/Linux and Git Bash; on Windows PowerShell use `$env:KEY="..."` instead.',
    ]
    for provider in ("groq", "gemini"):
        lines.append("")
        if provider == "groq":
            lines.append("GROQ (default run order uses GROQ first):")
        else:
            lines.append("GEMINI:")
        for shell_label, command in setup_commands(provider):
            lines.append(f"  {shell_label:<27} {command}")
    lines.append("")
    lines.append("Create a key at console.groq.com (Groq) or AI Studio at ai.google.dev (Gemini).")
    return "\n".join(lines)
