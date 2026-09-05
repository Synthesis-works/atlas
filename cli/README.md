# Atlas CLI

Command-line interface for the Atlas evaluation platform.

`atlas` talks to the Atlas control-plane API to manage benchmarks, models, runs,
and reports. The CLI distribution bundles the Atlas SDK (`atlas_sdk`) and the
internal LLM layer (`packages.llm`) that powers the agent brain, so a single
`pip install atlas-cli` is fully self-contained.

## Install

```bash
pip install atlas-cli
```

- Python 3.11+ is required.
- No `atlas-sdk` dependency is pulled from PyPI — the SDK ships inside the wheel
  (the PyPI `atlas-sdk` name belongs to an unrelated project).

## Quick start

```bash
# point at the Atlas API (defaults to http://localhost:8000)
export ATLAS_BASE_URL="https://api.example.com"

# authenticate (token is saved in %APPDATA%\Atlas\config.toml, never in the repo)
atlas login
atlas whoami
```

## Commands

- `atlas health` — check API health
- `atlas leaderboard` — model / benchmark leaderboards
- `atlas benchmark` — benchmark operations
- `atlas models` — model operations
- `atlas report` — execution reports
- `atlas run` — start executions
- `atlas dashboard` — dashboard summaries
- `atlas activity` — recent activity
- `atlas agent` — interactive agent (requires a provider key)

Run `atlas --help` for the full command list.

## Agent

The agent brain uses an LLM provider. Set one of:

```bash
export GEMINI_API_KEY="..."
export GROQ_API_KEY="..."
```

Then run `atlas agent "your task"`. With no key configured the agent refuses to
start and points you at the missing environment variable.

## Development

```bash
pip install -e ./sdk/python -e ./cli   # editable install from the monorepo
```

This installs the CLI and SDK as editable packages; `packages.llm` resolves to
the bundled copy inside the CLI layout (see `pyproject.toml`).

## License

Copyright (c) 2026. All rights reserved.