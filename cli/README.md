# Atlas CLI

Command-line interface for the Atlas evaluation platform.

`atlas` talks to the Atlas control-plane API to manage benchmarks, models, runs, and
reports. The CLI distribution bundles the Atlas SDK (`atlas_sdk`) and the
internal LLM layer (`packages.llm`) that powers the agent brain, so a single
`pip install synthesis-atlas-cli` is fully self-contained.

## Install

The package on PyPI is **`synthesis-atlas-cli`**; once installed, the command
you run is **`atlas`**.

```bash
pip install synthesis-atlas-cli
```

- Python 3.11+ is required.
- No `atlas-sdk` dependency is pulled from PyPI — the SDK ships inside the wheel
  (the PyPI `atlas-sdk` name belongs to an unrelated project).

## Quick start

```bash
# 1. Verify the install
atlas --version

# 2. Authenticate against the hosted Atlas API (the default — no configuration needed)
atlas login

# 3. Confirm your identity
atlas whoami

# 4. Browse the full command list
atlas --help
```

Atlas CLI targets the hosted Atlas API by default. To connect to a local or
self-hosted Atlas deployment, override the endpoint with `ATLAS_BASE_URL` or
`--base-url`:

```bash
export ATLAS_BASE_URL="http://localhost:8000"   # local / self-hosted
# or, per command:
atlas --base-url "http://localhost:8000" health
```

## Commands

- `atlas health` — check API health
- `atlas leaderboard` — model / benchmark leaderboards
- `atlas benchmark` — benchmark operations
- `atlas model` — model operations
- `atlas report` — execution reports
- `atlas run` — start executions
- `atlas dashboard` — dashboard summaries
- `atlas activity` — recent activity

These are deterministic, scriptable operations (human, JSON, or quiet output via
`--output`). Run `atlas --help` for the full command list.

## Agent

The agentic side of the CLI runs an LLM brain directly in your terminal. It
comes in two shapes:

- **Interactive REPL** — run bare `atlas` in a terminal to start a
  Gemini-CLI-style conversation:
  ```bash
  atlas
  ```
- **One-shot task** — run a single quoted task non-interactively:
  ```bash
  atlas agent "List the available benchmarks"
  ```

The agent brain uses an LLM provider. Set one of:

```bash
export GEMINI_API_KEY="..."
export GROQ_API_KEY="..."
```

With no key configured the agent refuses to start and points you at the missing
environment variable.

## Development

```bash
pip install -e ./sdk/python -e ./cli   # editable install from the monorepo
```

This installs the CLI and SDK as editable packages; `packages.llm` resolves to
the bundled copy inside the CLI layout (see `pyproject.toml`).

The CLI version is defined once in `cli/cli/__init__.py` (`__version__`) and is
picked up dynamically by `pyproject.toml`. See
[docs/guides/atlas-cli-release.md](../docs/guides/atlas-cli-release.md) for the
release-time staging build, offline artifact validation, and the (not yet enabled)
PyPI publishing workflow.

## License

Copyright (c) 2026. All rights reserved.