# Atlas CLI — Manual Testing Guide

- **Date:** 2026-08-28 (revised after the installable-CLI sprint — `atlas login`/`logout` + persisted credentials)
- **Branch:** `feature/atlas-cli-skeleton`
- **HEAD:** `1d446f1` (`feat(cli): add login and logout commands`)
- **Applies to:** `atlas-cli` 0.1.0 (`D:\atlas\cli`) + `atlas-sdk` 0.1.0 (`D:\atlas\sdk\python`)
- **Source of truth:** The installed/editable CLI source at `cli/cli/` (NOT the older architecture spec).
- **Audit method:** every command, option, exit code, and expected output in this guide was read from the actual implementation AND verified live against a local backend running at `http://localhost:8000` with the developer SQLite database `D:\atlas\atlas_dev.db`.

Use this document to manually exercise the CLI end-to-end. It has two audiences: a human developer, and an agent that drives `atlas` programmatically with `--output json`.

---

## ⚡ Quickstart (do this first)

On this machine the CLI and SDK are **already installed** editable (see §2 for what to do if they aren't). Once installed, `atlas` is a real command-line program — no `PYTHONPATH`, no `ATLAS_TOKEN` gymnastics.

**Step 1 — make sure `atlas` is on `PATH`** (run once per shell session):

```powershell
$env:PATH += ";C:\Users\Sujal\AppData\Local\Python\pythoncore-3.14-64\Scripts"
```

(Add that Scripts folder to the *persistent* user `PATH` via `[Environment]::SetEnvironmentVariable("PATH", $env:USERPROFILE + ";...\Scripts", "User")` if you want `atlas` in every new shell.)

**Step 2 — confirm the backend is up:**

```powershell
atlas health
```

Expect an `Atlas Health` block and exit 0. If it says `unreachable`/exit 6, start the backend (§3).

**Step 3 — authenticate once, then never again in this shell:**

```powershell
'password123' | atlas login --email demo@atlas.val --password-stdin
atlas whoami
atlas leaderboard model mock
```

`atlas login` stores the token (and the active base URL) in `%APPDATA%\Atlas\config.toml` and **never prints it**. From then on every `atlas` command auto-authenticates from the saved profile. `atlas logout` removes the stored token.

Then jump to §8 for the full copy/paste test sequence.

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python | 3.11+ (this guide verified on Python 3.14) |
| Atlas backend | Running and reachable, default `http://localhost:8000` |
| A user account | Any account the backend can authenticate (see §4) |
| Repo | `D:\atlas` checked out on `feature/atlas-cli-skeleton` |
| Package manager | `uv` (canonical) or `pip` (verified alternative) |

Nothing else is required for the read-only commands. `run submit` and `run cancel` mutate backend state and are the only commands that can create/change data — treat those as the exception (see §7.3).

---

## 2. Install the SDK and CLI locally

### 2.0 Check whether they're already installed (recommended)

On the dev machine both packages are **already installed editable** (source changes apply immediately, no reinstall ever needed):

```powershell
python -m pip show atlas-cli atlas-sdk        # two entries with "Editable project location"
atlas --version                               # "atlas, version 0.1.0" — or add Scripts to PATH (§2.3)
```

If you see them, **skip straight to the Quickstart** and do NOT run `pip install` again.

> **Why a plain `pip install` can fail here:** `pip install -e …` (and `uv pip install -e …`) first create an isolated build environment and **download `setuptools` and the deps from PyPI**. When `pypi.org` is unreachable those commands die with `NameResolutionError` / `No such host is known.` — BEFORE touching anything. That error does NOT mean the CLI is missing or broken; use the offline path in §2.1. Fresh-machine online install (`pip install -e ./sdk/python -e ./cli` into a clean venv) was verified 2026-08-28: deps resolve from PyPI, editable wheels build, and the resulting `atlas` console script works from any folder.

### 2.1 Offline install — everything needed is already in your Python env

Use `--no-build-isolation` (use the locally installed setuptools instead of downloading it) and `--no-deps` (click/httpx/pydantic are already present):

```powershell
# from the repo root
python -m pip install --no-build-isolation --no-deps -e ./sdk/python -e ./cli
```

Verified 2026-08-27: completes in seconds with `Successfully installed atlas-cli-0.1.0 atlas-sdk-0.1.0`.

### 2.2 Online install — use this only if internet is available

```powershell
# from the repo root
python -m pip install -e ./sdk/python -e ./cli
```

### 2.3 How to actually run `atlas` (3 options — all verified)

| # | Option | Command | Works from any folder? | Notes |
|---|---|---|---|---|
| A | Recommended | `atlas <args>` — after adding `C:\Users\Sujal\AppData\Local\Python\pythoncore-3.14-64\Scripts` to `PATH` | yes | Installed console script. Fully bypasses the folder-name clash. Used throughout this guide. |
| B | Ad-hoc runner | `$env:PYTHONPATH="D:\atlas\cli;D:\atlas\sdk\python"` (once per shell), then `python -c "from cli.app import main; main()" <args>` | yes | Same behavior as A incl. exit-2 usage errors; no PATH change needed. |
| C | cd into the package dir | `cd D:\atlas\cli`, then `python -c "from cli.app import main; main()" <args>` | only `D:\atlas\cli` | Good fallback if you don't want to set an env var. |

> **`uv` is NOT a drop-in for the CLI here.** The repo's root `uv sync` installs the `atlas` *app*, not the CLI. If you want a Poetry/`uv`-managed venv plus the CLI installed into it, install the CLI inside that venv (`& <venv>\Scripts\python -m pip install -e .\sdk\python -e .\cli`). Do not run `uv` at the repo root expecting the CLI to appear.

Verify, from any folder:

```powershell
atlas --version
# atlas, version 0.1.0
```

---

## 3. Start Atlas locally

### 3.1 One-click launcher (backend + worker + frontend)

`start_atlas.cmd` at the repo root starts everything and seeds demo data. Requirements: a `.venv` (create with `uv sync` in the repo root) and free ports 8000/5173.

```cmd
cd D:\atlas
start_atlas.cmd
```

It runs (all reported from `start_atlas.cmd`):
- Backend: `uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000`
- Outbox sweep loop (post-execution evaluation/snapshots)
- Frontend: `apps/landing` dev server on `http://localhost:5173`
- Seeds: database schema, login users, and demo benchmarks/executions/leaderboard/reports

### 3.2 Backend only (as currently running for this guide)

```powershell
$env:PYTHONPATH="D:\atlas;D:\atlas\packages\database;D:\atlas\packages;D:\atlas\services"
$env:DATABASE_URL="sqlite:///D:/atlas/atlas_dev.db"
$env:CELERY_TASK_ALWAYS_EAGER="true"
python -m uvicorn apps.backend.main:app --host 0.0.0.0 --port 8000
```

> **⚠ Do NOT start a second backend while one is already running.** If `uvicorn` exits immediately with `Application startup failed` and a `password authentication failed` error for `db….supabase.co`, it means the port was already taken by an existing local instance and this new process fell back to looking up the **production** Postgres DSN (because `DATABASE_URL` wasn't set). Leave the original instance (PID 13252) running. An already-running backend answers `http://localhost:8000/health` with `ok` — that's expected, not a conflict.

### 3.3 Verify backend health

```powershell
Invoke-RestMethod http://localhost:8000/health            # {"status":"ok","version":"1.0.0"}
atlas health
atlas --output json health
```

---

## 4. Authentication

There are **two** ways to give the CLI a bearer token:

1. `atlas login` — the interactive way. Prompts for email and password, calls the backend login API, and **persists** the token to the per-user profile file `%APPDATA%\Atlas\config.toml` (default profile name `default`). **Never prints the token.**
2. `ATLAS_TOKEN` environment variable — overrides the stored token for scripts/CI.

`atlas logout` deletes the stored token (keeps the saved base URL) and works with no backend connection.

### 4.1 `atlas login`

```powershell
# interactive (prompts for email + hidden password)
atlas login

# non-interactive: --email plus the password piped on stdin (one line)
'password123' | atlas login --email demo@atlas.val --password-stdin

# JSON receipt — note it does NOT contain the token
atlas --output json login --email demo@atlas.val --password-stdin
# → {"success": true, "email": "demo@atlas.val", "base_url": "http://localhost:8000", "profile": "default"}
```

On success the active base URL and the access token are written together; on password/HTTP failure **nothing** is persisted (exit code = mapped error, e.g. 3 for bad credentials). Empty stdin with `--password-stdin` → exit 7.

### 4.2 The profile file

```text
C:\Users\<you>\AppData\Roaming\Atlas\config.toml
```

```toml
[default]
base_url = "http://localhost:8000"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Read with stdlib `tomllib`; a corrupt or missing file is ignored (CLI falls back to defaults). Passwords are never stored — only the JWT.

### 4.3 `atlas logout`

```powershell
atlas logout             # "Logged out" — removes token, keeps base_url
atlas --output json logout   # {"success": true, "logged_out": true, "profile": "default"}
```

Succeeds (exit 0) even when nothing is stored. Does not contact the backend.

### 4.4 With no credentials at all

Authenticated commands fail fast (with or without a profile):

```powershell
atlas whoami
# error: Not authenticated — run `atlas login` or set ATLAS_TOKEN.   (see note in §10.8)
# exit code 3
```

`health` is the one exception — it works without a token (the endpoints are public).

---

## 5. Invocation patterns and global options

### 5.1 Global options — MUST come before the subcommand

All global options are defined on the top-level `atlas` group (see `cli/app.py`) and Click requires them **before** the command name. Placing them after the subcommand is a usage error.

```powershell
atlas --output json whoami        # OK
atlas --output json report list   # OK
atlas whoami --output json        # Error: No such option: --output  (exit 2)
```

> **⚠ Known trap — folder-name clash (`ImportError` from repo root):** the repo contains BOTH the folder `D:\atlas\cli\` (package's *parent*) and the actual package inside it, `D:\atlas\cli\cli\`. From the repo root, `import cli` silently grabs the empty parent folder as a namespace package and crashes:
>
> ```text
> ImportError: cannot import name '__version__' from 'cli' (unknown location)
> ```
>
> The **installed `atlas` console script is immune** — it is the recommended way to run the CLI (§2.3). The ad-hoc `python -c` runner needs `$env:PYTHONPATH="D:\atlas\cli;D:\atlas\sdk\python"` or running from `D:\atlas\cli`.

| Global option | Long / short | Values | Env var | Effect |
|---|---|---|---|---|
| Output mode | `--output` / `-o` | `human` (default) \| `json` \| `quiet` (case-insensitive) | `ATLAS_OUTPUT` | Selects output rendering |
| Quiet shorthand | `--quiet` / `-q` | flag | — | Forces quiet mode (overrides `--output`) |
| Base URL | `--base-url` | URL | `ATLAS_BASE_URL` | API base (default `http://localhost:8000`) |
| Profile | `--profile` | name | `ATLAS_PROFILE` | Profile section read/written in `%APPDATA%\Atlas\config.toml` (default `default`) |
| Timeout | `--timeout` | float seconds | `ATLAS_TIMEOUT` | Request timeout (default `60.0`) |
| Retries | `--retries` | integer ≥ 0 | `ATLAS_RETRIES` | Max retries for idempotent GET/HEAD requests (default `3`); `0` disables them |
| No color | `--no-color` | flag | — | Disables ANSI colors |
| Version | `--version` / `-V` | flag | — | Prints `atlas, version 0.1.0` and exits 0 |

Precedence (highest wins): **CLI flag > environment variable > saved profile > built-in default** (`cli/config.py`). A token, when set, comes from `ATLAS_TOKEN` (env) or the saved profile — flags do not take a token.

**Retry semantics:** `--retries` (default `3`, matching the SDK) controls the SDK's built-in retry loop, which applies **only to idempotent GET/HEAD requests** on transient failures (429, 5xx, or transport errors). `run submit` (POST) and other non-idempotent calls are **never** automatically retried, regardless of `--retries`. Negative values and non-integers are usage errors (exit 2).

### 5.2 Bare invocations

```powershell
atlas --help
atlas            # same as --help (invoke_without_command)
atlas --version
```

Current command tree:

```text
atlas
├─ login
├─ logout
├─ whoami
├─ health
├─ dashboard [--json-schema]
├─ activity [--type benchmarks|executions|models] [--limit]
├─ benchmark
│  ├─ list [--json-schema]
│  ├─ get BENCHMARK_ID [--json-schema]
│  └─ versions BENCHMARK_ID
├─ leaderboard
│  ├─ benchmark BENCHMARK_ID [--limit] [--offset] [--json-schema]
│  └─ model MODEL_NAME [--history | --benchmarks] [--json-schema]
├─ run
│  ├─ submit BENCHMARK_VERSION_ID --target-model [--dataset-version-id] [--preview]
│  ├─ get EXECUTION_ID [--json-schema]
│  ├─ list [--benchmark-version-id] [--status] [--limit] [--offset]
│  ├─ watch EXECUTION_ID [--interval]
│  └─ cancel EXECUTION_ID
└─ report
   ├─ list [--status] [--benchmark-id] [--benchmark-version] [--target-model] [--limit] [--offset]
   ├─ get RUN_ID [--json-schema]
   └─ export RUN_ID [--format] [--output-file] [--include-prompt] [--include-expected-output] [--force]
```

**Schema self-description (`--json-schema`):** the commands marked `[--json-schema]` print the **JSON Schema document** describing that command's JSON output and exit 0 — resolved **offline from the pydantic model**, no backend round-trip (works exactly like `--help`), deterministic, and machine-readable for agents. Commands *without* the flag reject it as an unknown option (exit 2). `--quiet` still wins (silent, exit 0). Only commands whose JSON output is a faithful model dump expose the flag: `activity`, `run list`, `run cancel`, `report list`, `report export`, `benchmark versions`, and `health` deliberately do not.

---

## 6. Exit codes

Defined in `cli/errors.py`; commands exit via `error_exit()` (`cli/output/errors.py`).

| Code | Meaning | Typical trigger |
|---|---|---|
| 0 | Success | — |
| 1 | Unspecified / server / degraded | Backend 5xx; `health` when any probe is unreachable |
| 2 | Usage error | Unknown option, bad choice (`--format xml`), unknown command, or mutually exclusive flags (e.g. `leaderboard model --history --benchmarks`). Clean `Error: …` on stderr — no traceback. |
| 3 | Auth required | Missing/invalid/expired token; 401 |
| 4 | Forbidden | 403 (e.g. project/org membership) |
| 5 | Not found | 404 (e.g. unknown run/execution) |
| 6 | Network | Connection refused / DNS / timeout |
| 7 | Validation | 422 from backend |
| 8 | Conflict | `report export` destination already exists without `--force` |
| 9 | Watch timed out | `run watch` reached its `--timeout` bound while the execution was still non-terminal (e.g. QUEUED/RUNNING) |
| 130 | Interrupted | Ctrl-C during `run watch` |

---

## 7. Command reference

Conventions used below:
- `A=` prefix means the arg is required.
- An example "simple verification anchor" that is known to work with the current seeded DB on this machine is given per command (obtained live). IDs are shown so you can copy them, but §8 shows how to obtain them yourself from earlier commands.
- Runner used: the installed `atlas` console script (see §2.3). Commands are shown with the global option **before** the subcommand.

### Schema self-description — `--json-schema`

```powershell
atlas dashboard --json-schema                     # full DashboardSnapshot schema ($defs/$ref), exit 0
atlas run get 2e56f6ec-dc98-4b18-a8cc-46d931e80ace --json-schema     # ExecutionResponse schema
atlas report get b94248f7-f5f9-4ed8-992a-b29751b4e710 --json-schema  # nested scores[] via $defs/CapabilityScoreRead
atlas benchmark list --json-schema                # PageResponse[BenchmarkRead]
atlas benchmark get 44444444-4444-4444-4444-444444444444 --json-schema
atlas leaderboard benchmark 181d1c91-15f9-43e7-866d-33809aaaedf1 --json-schema
atlas leaderboard model mock --json-schema        # ModelSummary
atlas leaderboard model mock --history --json-schema   # array[TrendPoint] ("type": "array")
atlas leaderboard model mock --benchmarks --json-schema
atlas --quiet dashboard --json-schema; echo "exit=$LASTEXITCODE"    # 0, silent
atlas activity --json-schema; echo "exit=$LASTEXITCODE"              # 2 — outside the faithful-model set
```

All of the above work with the backend stopped — the schema is derived from the SDK models at parse time. The document uses draft 2020-12 (`"$schema"` at the top) with nested DTOs expressed through `$defs`/`$ref`.

### 7.1 `atlas whoami`

- **API:** `GET /api/v1/auth/me`
- **Args/options:** none
- **Auth:** required (exit 3 if neither `ATLAS_TOKEN` nor a saved profile is present)

```powershell
atlas whoami
atlas --output json whoami
atlas --quiet whoami
```

Human output (verified):

```text
Atlas User

         Email:  cli-test2@atlas.dev
          Name:  CLI Test 2
       User ID:  4ea0f4ae-9727-4030-adeb-13837f051e64
  Organization:  (none)
        Active:  yes
      Verified:  no
```

JSON output (machine keys: `id`, `email`, `full_name`, `is_active`, `is_verified`, `org_id`). Quiet mode: no output, exit 0. Errors: 401 → 3, 403 → 4, network → 6.

### 7.2 `atlas health`

- **API:** `GET /health`, `GET /api/v1/system/health/live`, `GET /api/v1/system/health/ready`
- **Args/options:** none
- **Auth:** not required

```powershell
atlas health
atlas health --output json
atlas --quiet health
```

Human output (verified, healthy backend):

```text
Atlas Health

   API Status:  ok
  API Version:  1.0.0
     Liveness:  alive
    Readiness:  ready
     database:  connected
      Overall:  healthy
```

JSON shape (verified — keys `api`, `liveness`, `readiness`, `overall`):

```json
{
  "api": { "status": "ok", "version": "1.0.0" },
  "liveness": { "status": "alive", "version": "0.9.0" },
  "readiness": { "status": "ready", "checks": { "database": "connected" } },
  "overall": "healthy"
}
```

Any single probe failing makes `overall` `degraded` **and exit code 1** (all output modes). Note the `liveness.version` (0.9.0) differs from `/health`'s 1.0.0 — that is backend behavior, not a CLI bug.

### 7.3 `atlas run …`

> `run submit` (without `--preview`) and `run cancel` create/change backend state. Use them only if you intend to actually invoke a (eager) execution or cancel one. `--preview` is strictly read-only. Everything else in this guide is read-only.

#### `atlas run submit BENCHMARK_VERSION_ID`

- **API:** `POST /api/v1/benchmarks/{id}/executions`
- **Options:** `--target-model TEXT` (**required** — no default; v2 removed the silent `gemini-2.5-flash` default), `--dataset-version-id TEXT` (default: resolved from benchmark version), `--preview` (read-only dry-run; **no POST**)
- **Warning:** without `--preview`, creates a real execution (QUEUED then dispatched by the eager worker).
- **`--preview` plan:** resolved from `GET /api/v1/executions/dispatch-targets` (the exact dispatchable set — published benchmarks + any benchmark draft in organizations you actively belong to), prints `benchmark_version_id`, `benchmark_name`, `version_string`, `dataset_version_id`, `target_model`, `adapter_kind` (`mock|mocked` → `mock`, else `real`), `preview: true`, and a "no execution created" note. Exit 0. A version that is NOT a dispatchable target → exit 5, message "not a dispatchable target (unknown, unpublished, or not in your organizations)" — covers both nonexistent IDs and real drafts you lack membership for (dispatch-targets omits them rather than returning 403).

```powershell
atlas run submit 55555555-5555-5555-5555-555555555555                                 # exit 2: Missing option '--target-model'
atlas run submit 55555555-5555-5555-5555-555555555555 --target-model mock --preview   # exit 0, plan, NO run created
atlas run submit 55555555-5555-5555-5555-555555555555 --target-model mock             # exit 0, QUEUED (real execution)
atlas run submit cd9e64fc-a4d9-42ca-aff3-b818da63c352 --target-model mock             # draft, non-member → exit 4
atlas run submit 00000000-0000-0000-0000-000000000000 --target-model mock --preview   # exit 5, no POST
```

#### `atlas run get EXECUTION_ID`

- **API:** `GET /api/v1/executions/{id}`
- **Anchor (verified):** `b94248f7-f5f9-4ed8-992a-b29751b4e710`

```powershell
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710 --output json
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710 --json-schema
```

Verified human output (see §10.9 for a status note on this specific ID):

```text
Execution

       Execution ID:  b94248f7-f5f9-4ed8-992a-b29751b4e710
             Status:  RUNNING
       Target Model:  mock
  Benchmark Version:  181d1c91-15f9-43e7-866d-33809aaaedf1
           Progress:  0/1
        Max Retries:  3
            Created:  2026-08-23T07:04:07.208216
            Updated:  2026-08-26T05:16:51.480549
```

Unknown ID → 404 → exit 5. No token → 401 → exit 3.

#### `atlas run list`

- **API:** `GET /api/v1/executions`
- **Options:** `--benchmark-version-id TEXT`, `--status TEXT` (e.g. `COMPLETED`, `FAILED`, `CANCELLED` — free-form, not a Click Choice), `--limit INTEGER` (default 20), `--offset INTEGER` (default 0)

```powershell
atlas run list
atlas run list --limit 5 --status COMPLETED --output json
atlas --quiet run list
```

Human table columns: `ID` (first 8 chars), `Status`, `Model`, `Progress`, `Created`; prints `Showing X of Y` when truncated. JSON keys: `items`, `total`, `limit`, `offset`.

#### `atlas run watch EXECUTION_ID`

- **API:** polls `GET /api/v1/executions/{id}`
- **Options:** `--interval FLOAT` (default `3.0`, must be > 0); `--timeout FLOAT` (must be > 0 when set; omitted = unbounded, v1 behavior)
- Polls until status ∈ {`COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`}; prints progress to stderr in human mode, final state once. Ctrl-C → exit 130. After 3 consecutive network errors → exit 1.
- `--timeout` bounds the wait by wall clock (each poll's sleep is capped so the deadline is not overslept). On expiry:
  - exit **9** (WATCH_TIMEOUT);
  - JSON mode emits the **last observed non-terminal** execution on stdout (empty stdout if no state was ever observed);
  - human mode prints `timed out after <N>s — status <STATUS> (x/y items); re-run with a larger --timeout` to stderr;
  - quiet mode stays completely silent.

```powershell
atlas run watch b94248f7-f5f9-4ed8-992a-b29751b4e710 --interval 2
atlas run watch b94248f7-f5f9-4ed8-992a-b29751b4e710 --timeout 30
atlas --output json run watch b94248f7-f5f9-4ed8-992a-b29751b4e710 --timeout 30   # exit 9 + last state on expiry
atlas --quiet run watch b94248f7-f5f9-4ed8-992a-b29751b4e710 --timeout 30          # exit 9, silent
```

#### `atlas run cancel EXECUTION_ID`

- **API:** `POST /api/v1/executions/{id}/cancel` (sets the cooperative cancellation flag; NOT idempotent)
- Terminal-state execution → backend 409 → exit 8.

```powershell
atlas run cancel <EXECUTION_ID>
```

> Prefer a running/queued ID. Cancelling an already-terminal execution is expected to fail with 409 → exit 8.

### 7.4 `atlas benchmark …`

> **Note:** **published** benchmarks are readable by any authenticated user, so `benchmark get`/`versions` work for every test credential. **Draft** benchmarks are org-gated: a non-member gets 403 (exit 4) — see §10.3.

#### `atlas benchmark list`

- **API:** `GET /api/v1/benchmarks` (fixed `limit=50` in the CLI)
- **Args/options:** none

```powershell
atlas benchmark list
atlas benchmark list --output json
atlas benchmark list --json-schema
atlas --quiet benchmark list
```

Verified human output is a table (`Name`, `ID`, `State`) listing the 8 published benchmarks; empty result prints `  (no benchmarks)`. JSON keys: `items`, `total`, `limit`, `offset`, `next_cursor`.

#### `atlas benchmark get BENCHMARK_ID` / `atlas benchmark versions BENCHMARK_ID`

- **API:** `GET /api/v1/benchmarks/{id}`, `GET /api/v1/benchmarks/{id}/versions`
- **Anchor (published → exit 0 for any logged-in user):** `44444444-4444-4444-4444-444444444444` (HumanEval), version `55555555-5555-5555-5555-555555555555`
- **Draft anchor (→ exit 4 for non-members):** `cd9e64fc-a4d9-42ca-aff3-b818da63c352`

```powershell
atlas benchmark get 44444444-4444-4444-4444-444444444444      # published → exit 0
atlas benchmark versions 44444444-4444-4444-4444-444444444444  # published → exit 0
atlas benchmark get cd9e64fc-a4d9-42ca-aff3-b818da63c352       # draft, non-member → exit 4
```

`get` human output: `Name`, `ID`, `Project ID`, `State`; JSON = benchmark object dump. `versions` human output: `Version`, `ID`, `State`; JSON = `{"items": [...], "total": N}`.

### 7.5 `atlas report …`

#### `atlas report list`

- **API:** `GET /api/v1/reports/runs`
- **Options:** `--status` (Click Choice: `pending|running|evaluating|completed|partial_success|failed|cancelled`), `--benchmark-id TEXT`, `--benchmark-version TEXT`, `--target-model TEXT`, `--limit INTEGER` (default 50), `--offset INTEGER` (default 0)

```powershell
atlas report list
atlas report list --status completed --output json
atlas --quiet report list
```

Verified human output:

```text
Report Runs

  Run ID    Model             Version  Status  Score  Completed
  --------  ----------------  -------  ------  -----  ----------------
  ff0a7a03  gemini-2.5-flash  1.0.0    FAILED  -      2026-08-26 06:24
```

JSON keys (verified): `items`, `total`, `page`, `size` (note: differs from `run list` which uses `limit`/`offset`).

#### `atlas report get RUN_ID`

- **API:** `GET /api/v1/reports/runs/{run_id}`
- **Anchor (verified, exit 0):** `b94248f7-f5f9-4ed8-992a-b29751b4e710`

```powershell
atlas report get b94248f7-f5f9-4ed8-992a-b29751b4e710
atlas report get b94248f7-f5f9-4ed8-992a-b29751b4e710 --output json
atlas report get b94248f7-f5f9-4ed8-992a-b29751b4e710 --json-schema   # nested scores via $defs/CapabilityScoreRead
```

Verified human output:

```text
Report Summary

         Run ID:  b94248f7-f5f9-4ed8-992a-b29751b4e710
      Benchmark:  Python Vulnerability Detection Benchmark
        Version:  1.0.0
          Model:  mock
         Status:  COMPLETED
        Started:  2026-08-26 05:16
      Completed:  -
  Overall Score:  100.0
```

Unknown RUN_ID → 404 → exit 5. No token → 401 → exit 3. Note: the JSON error body uses an `error` envelope (`{"error": {"status", "code", "message", "details"}}`).

#### `atlas report export RUN_ID`

- **API:** `GET /api/v1/reports/runs/{run_id}/export`
- **Anchor (verified, exit 0):** `b94248f7-f5f9-4ed8-992a-b29751b4e710`
- **Options:**
  | Option | Meaning |
  |---|---|
  | `--format [json\|csv]` | Default `json` (case-insensitive Choice; anything else = usage error, exit 2) |
  | `--output-file TEXT` | Destination path; `-` = raw bytes to stdout; default = server-provided filename in the current directory |
  | `--include-prompt` | Include original prompts in the export |
  | `--include-expected-output` | Include expected outputs in the export |
  | `--force` | Allow overwriting an existing destination |

```powershell
# default: server-provided filename in cwd, human receipt
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710
# → Exported report to python-vulnerability-detection-benchmark-evaluation-report-v1.0.0.json (2929 bytes)

# explicit path, JSON receipt
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file my-report.json --output json
# → {"path": "my-report.json", "bytes": 2929, "content_type": "application/json"}

# CSV
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --format csv --output-file my-report.csv

# raw bytes to stdout (nothing else on stdout — verified byte-identical to the file)
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file -

# include prompt/expected output values (verified: 2929 → 3620 bytes)
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --include-prompt --include-expected-output --output-file full.json

# overwrite protection: second run → exit 8, "Destination already exists: <dest> (use --force to overwrite)."
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file my-report.json
atlas report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file my-report.json --force
```

Behavior notes (all verified live):
- `--output-file -` writes **only** the raw bytes; no receipt is mixed in, even in `--output json` mode.
- Default destination comes from the server's `Content-Disposition` (slugified `title-v<version>.json`), else `report-<run-id>.<ext>`.
- Receipts: human `Exported report to <path> (<n> bytes)`; JSON `{"path","bytes","content_type"}`; quiet = nothing.
- Unknown RUN_ID → 404 → **exit 5** (this is the behavior added in commit `db34e3d`).
- No token → 401 → exit 3.
- Invalid `--output-file` location (e.g. non-existent parent dir) → Python `FileNotFoundError` propagates as an unhandled traceback with a non-zero exit (see §10.6).

### 7.6 `atlas leaderboard …`

#### `atlas leaderboard benchmark BENCHMARK_ID`

- **API:** `GET /api/v1/benchmarks/{benchmark_version_id}/leaderboard`
- **Options:** `--limit INTEGER` (default 20), `--offset INTEGER` (default 0)
- **Anchor (403 for test users — §10.3):** `66666666-6666-6666-6666-666666666666`

```powershell
atlas leaderboard benchmark 66666666-6666-6666-6666-666666666666      # → exit 5 currently (unknown version id → 404)
atlas leaderboard benchmark 66666666-6666-6666-6666-666666666666 --limit 50
atlas leaderboard benchmark 181d1c91-15f9-43e7-866d-33809aaaedf1 --json-schema
```

Human output is a ranked table (`Rank`, `Model Name`, `Avg Score %`, `Runs`, `Last Run At`); JSON = ranked model dump.

#### `atlas leaderboard model MODEL_NAME [--history | --benchmarks]`

- **API:** summary `GET /api/v1/models/{name}/summary`; history `GET /api/v1/models/{name}/history`; benchmarks `GET /api/v1/models/{name}/benchmarks`
- **Options:** `--history` / `--benchmarks` are **mutually exclusive** (both → usage error, exit 2)
- **Anchor (verified, exit 0):** `mock`

```powershell
atlas leaderboard model mock                    # summary block / table
atlas leaderboard model mock --history          # per-run execution history
atlas leaderboard model mock --benchmarks       # per-benchmark breakdown
atlas leaderboard model mock --json-schema     # ModelSummary; --history → array[TrendPoint]; --benchmarks → array[ModelBenchmarkHistory]
atlas leaderboard model mock --history --benchmarks; echo "exit=$LASTEXITCODE"   # 2
atlas leaderboard model does-not-exist --benchmarks; echo "exit=$LASTEXITCODE"   # 0, "(no benchmark data)"
```

Default summary (no flag) shows model `Avg Score`, total/`Computed`/`Healthy` runs, and the last run timestamp; `--history` renders each execution (`Timestamp`, `Status`, `Score`, `Execution ID`); `--benchmarks` propagates each benchmark's `Name`, `Version`, run count, latest `Score`, `Timestamp`, `Execution ID` (latest = max `(timestamp, execution_id)`). Unknown model names are **not** an error — they print `(no data)` / `(no benchmark data …)` and exit 0.

### 7.7 `atlas dashboard`

- **API:** `GET /api/v1/dashboard` (bare response, unauthenticated-friendly)
- **Args/options:** none

```powershell
atlas dashboard
atlas dashboard --output json
atlas dashboard --json-schema
atlas --quiet dashboard; echo "exit=$LASTEXITCODE"   # 0
```

Human output (verified) is three blocks: **Recent Runs** (a deduped table of job submissions — `Job ID`, `Benchmark`, `Model`, `Status`, `Queued`), **Recent Activity** (latest `Benchmark Read` / `Execution History` / `Model Activity` lines), and **Runtime Stats** (`DB`, `Storage`, `Queue`). Empty activity renders `(no recent activity)`. JSON keys match the SDK `DashboardSnapshot` (summary, hierarchy, running_jobs, recent_verified_runs, active_executions, activity, runtime, capability).

### 7.8 `atlas activity`

- **API:** `GET /api/v1/history/{benchmarks|executions|models}/recent?limit=N`
- **Options:** `--type [benchmarks|executions|models]` (default `benchmarks`), `--limit INTEGER` (default 10)

```powershell
atlas activity                                  # benchmarks by default
atlas activity --type executions --limit 5
atlas activity --type models
atlas activity --output json                    # only the requested section is included
atlas activity --type bogus; echo "exit=$LASTEXITCODE"    # 2 (invalid Choice)
```

Human output is a per-section `Recent <Type>` table (`Timestamp`, `Name`/`Status`/`ID` as appropriate). JSON payload contains **only** the requested type's key (`benchmarks`, `executions`, or `models` — verified), each entry dumping its `Recent*Read` fields.

---

## 8. End-to-end copy/paste smoke-test sequence

All commands below are **read-only** and were verified on this machine. Get `atlas` on `PATH` first:

```powershell
$env:PATH += ";C:\Users\Sujal\AppData\Local\Python\pythoncore-3.14-64\Scripts"
'password123' | atlas login --email demo@atlas.val --password-stdin   # one-time auth (see §8.11)
cd D:\atlas   # from the repo root so relative export paths are under D:\atlas
```

> If you'd rather drive the underlying `main()` entrypoint directly, define `$PY = "python -c `"from cli.app import main; main()`""`, invoke **it** in place of `atlas` below, and add the `$env:PYTHONPATH` line from §5.1.

### 8.1 Version and help

```powershell
atlas --version                    # atlas, version 0.1.0   (exit 0)
atlas --help                       # usage + commands        (exit 0)
atlas dashboard --help
atlas activity --help
atlas benchmark --help
atlas leaderboard model --help     # mentions --history and --benchmarks
atlas run --help
atlas report --help
```

### 8.2 Health (no auth needed)

```powershell
atlas health                       # human table, exit 0
atlas --output json health         # {"api":{...},"liveness":{...},"readiness":{...},"overall":"healthy"}
atlas --quiet health               # no output, exit 0
```

### 8.3 Human output

```powershell
atlas whoami                       # Atlas User block        (exit 0)
atlas benchmark list               # 8 published benchmarks  (exit 0)
atlas run list --limit 3           # executions table        (exit 0)
atlas report list --limit 3        # report runs table       (exit 0)
atlas report get b94248f7-f5f9-4ed8-992a-b29751b4e710   # Report Summary, score 100.0 (exit 0)
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710      # Execution detail            (exit 0)
```

### 8.4 JSON output

```powershell
atlas --output json whoami
atlas --output json health
atlas --output json benchmark list
atlas --output json run list --limit 3
atlas --output json report list --limit 3
atlas --output json report get b94248f7-f5f9-4ed8-992a-b29751b4e710
```

Every JSON command above exits 0 and prints one JSON document to stdout. Verify pass by piping to a JSON parser if you like.

### 8.5 Quiet mode

```powershell
atlas --quiet whoami; echo "exit=$LASTEXITCODE"        # 0
atlas -q benchmark list; echo "exit=$LASTEXITCODE"     # 0
atlas --quiet report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file smoke-quiet.json; echo "exit=$LASTEXITCODE"
```

### 8.6 Invalid / nonexistent IDs

```powershell
atlas run get 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"        # 5
atlas report get 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"      # 5
atlas report export 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"   # 5
atlas report list --status bogus; echo "exit=$LASTEXITCODE"                           # 2 (invalid Choice)
atlas report export x --format xml; echo "exit=$LASTEXITCODE"                         # 2 (invalid Choice)
```

### 8.7 Authentication failure

The saved profile is the live credential, so `Remove-Item Env:ATLAS_TOKEN` alone is NOT enough here — log out first:

```powershell
atlas logout
atlas whoami; echo "exit=$LASTEXITCODE"                             # 3  (Not authenticated)
atlas --output json whoami; echo "exit=$LASTEXITCODE"               # 3  (JSON error envelope on stderr)
# restore auth
'password123' | atlas login --email demo@atlas.val --password-stdin
atlas run list; echo "exit=$LASTEXITCODE"                           # 0
```

For a live 401 (expired/garbage token), set `$env:ATLAS_TOKEN="invalid"` and re-run `whoami` → the env var overrides the stored token → exit 3.

### 8.8 Forbidden access

```powershell
atlas benchmark get 66666666-6666-6666-6666-666666666666; echo "exit=$LASTEXITCODE"     # 4
atlas benchmark versions 66666666-6666-6666-6666-666666666666; echo "exit=$LASTEXITCODE" # 4
```

(Seeded published benchmarks belong to an org no seeded user belongs to — verified 403 behavior. See §10.4.)

### 8.9 Export matrix

```powershell
$RUN = b94248f7-f5f9-4ed8-992a-b29751b4e710
cd $env:TEMP

# JSON to server-provided filename in cwd
atlas report export $RUN            # receipt, exit 0

# CSV
atlas report export $RUN --format csv --output-file smoke.csv

# specified file, JSON receipt
atlas --output json report export $RUN --output-file smoke.json

# include prompt + expected output
atlas report export $RUN --include-prompt --include-expected-output --output-file full.json

# stdout (raw bytes, byte-identical to the file version)
atlas report export $RUN --output-file - > raw.bin
if ((Get-FileHash raw.bin).Hash -eq (Get-FileHash smoke.json).Hash) { "stdout==file: OK" }

# overwrite refusal then --force
atlas report export $RUN --output-file smoke.json; echo "exit=$LASTEXITCODE"  # 8
atlas report export $RUN --output-file smoke.json --force; echo "exit=$LASTEXITCODE"  # 0
```

### 8.10 Recommended ID discovery

Never guess IDs — take them from an earlier JSON/list command:

```powershell
# latest run/run-id (used by report get/export and run get)
atlas report list --limit 5 --output json            # items[].run_id
atlas run list --limit 5 --output json               # items[].id, items[].benchmark_version_id

# benchmark version id (needed only for `run submit`, which creates an execution)
atlas benchmark versions <BENCHMARK_ID> --output json   # items[].id
```

### 8.11 Login / logout smoke (live-verified)

```powershell
'password123' | atlas login --email demo@atlas.val --password-stdin   # "Logged in as demo@atlas.val"
atlas whoami                                                          # Atlas User block
atlas --output json whoami                                            # user JSON
atlas --quiet whoami; echo "exit=$LASTEXITCODE"                       # 0
atlas --base-url http://localhost:8000 login --email demo@atlas.val --password-stdin   # saves that base URL
atlas logout                                                          # "Logged out" (keeps base_url)
atlas logout                                                          # still exit 0 (idempotent)
atlas whoami; echo "exit=$LASTEXITCODE"                               # 3
Get-Content "$env:APPDATA\Atlas\config.toml"                          # [default] + base_url only, no token
```

### 8.12 Dashboard, activity, and model benchmark smoke (live-verified)

```powershell
# dashboard: human / json / quiet
atlas dashboard; echo "exit=$LASTEXITCODE"                            # 0, Runs + Activity + Runtime blocks
atlas --output json dashboard | Out-Null; echo "exit=$LASTEXITCODE"   # 0, one JSON doc
atlas --quiet dashboard; echo "exit=$LASTEXITCODE"                    # 0, no output

# activity: default and filtered
atlas activity; echo "exit=$LASTEXITCODE"                             # 0, Recent Benchmarks
atlas activity --type executions --limit 5; echo "exit=$LASTEXITCODE" # 0
atlas --output json activity --type models | Select-String '"models"' # JSON contains only the models key
atlas activity --type bogus; echo "exit=$LASTEXITCODE"                # 2, "Invalid value for '--type'"

# leaderboard model --benchmarks
atlas leaderboard model mock --benchmarks; echo "exit=$LASTEXITCODE"  # 0, per-benchmark breakdown
atlas leaderboard model unknown-model --benchmarks; echo "exit=$LASTEXITCODE"  # 0, "(no benchmark data)"
atlas leaderboard model mock --history --benchmarks; echo "exit=$LASTEXITCODE" # 2, mutually exclusive
```

---

## 9. Agent-friendly (machine-readable) usage

The CLI is designed agent-first: prefer `--output json` for anything the agent will parse.

- **Every command supports `--output json`** (optionally `--quiet` for exit-code-only checks).
- JSON goes to **stdout**, one document per invocation. Errors (JSON mode) go to **stderr** in the envelope `{"error": {"status", "code", "message", "details"}}`.
- Caveat: raw binary endpoints — `report export … --output-file -` — emit **bytes, not JSON**. Verify content type before `json.loads` on export output.
- Empty collections render as `{"items": [], "total": 0, ...}` (not `null`).
- Watch out for pagination key differences: `run list` returns `limit`/`offset`; `report list` returns `page`/`size`.
- Recommended pattern for a poll loop:

```bash
atlas ... --output json
# parse stdout as JSON; treat non-zero exit code as failure (see §6)
```

---

## 10. Known limitations and caveats

### 10.1 Not currently available
- PAT / machine-token authentication — not implemented (use `atlas login`, `ATLAS_TOKEN`, or `--base-url`).
- Multi-profile switching UX — config.toml supports multiple `[profile]` sections, but only the one named by `--profile`/`ATLAS_PROFILE` is read/written.
- TypeScript SDK — not consulted; this guide covers the Python SDK only.
- `run submit` with a real LLM target that yields actual API costs — the default `--target-model gemini-2.5-flash` hit a real provider adapter on this box; treat submit as potentially expensive.

### 10.2 Known unrelated backend test failures
- `test_execution_backend_routing.py`: 2 failures (pre-existing, execution backend routing).
- `test_d7_reporting_async.py`: 4 errors under SQLite (`TRUNCATE` not supported — PostgreSQL-only fixture). Run the reporting async tests against PostgreSQL to confirm; on the SQLite dev DB they error, not fail logic.

### 10.3 `benchmark get`/`versions` on draft benchmarks → 403 for non-members
**Published** benchmarks are readable by any authenticated user (verified live with `demo@atlas.val`: `benchmark get`/`versions` on HumanEval `44444444-…` exit 0). **Draft** benchmarks remain org-gated: a non-member of the owning project's org gets exit 4 (e.g. draft `cd9e64fc-…` in the "Default" project, whose org is `None`).

### 10.4 `run get` execution status is authoritative and report-consistent
`run get`/`run list`/`run watch` read the authoritative `executions` row (Slice 1 fix). Verified live: `b94248f7-f5f9-4ed8-992a-b29751b4e710` reports `COMPLETED` 3/3, matching `report get`.

### 10.5 Usage-error exit codes (fixed January 2026)
The console-script entrypoint previously surfaced Click usage errors as uncaught tracebacks with exit 1. `entrypoint()` now catches `click.ClickException` and prints `Error: <message>` to stderr, exiting with `exit_code` (2). Verified live: unknown command, invalid `--type` Choice, and mutually exclusive `--history --benchmarks` all → exit 2 with a one-line message and no traceback, for both the installed `atlas` script and the `python -c` form.
### 10.6 Unhandled local I/O exceptions

`report export` propagates a raw `FileNotFoundError`/`PermissionError` if the destination can't be opened (only the overwrite-refusal path yields the clean exit 8). Expect an unhandled traceback and a non-zero exit code in that case.

### 10.7 httpx prints `TLS verification disabled for localhost target` to stderr
This INFO line appears once per process for `localhost` targets. Harmless; it goes to stderr and does not affect stdout/exit codes. It is why `2>$null` appears in this guide's examples.

### 10.8 "Not authenticated — run `atlas login` or set ATLAS_TOKEN"
`whoami`'s no-token error (`cli/commands/auth.py`) is now fully accurate: `atlas login` exists and persists the token to `%APPDATA%\Atlas\config.toml`. `ATLAS_TOKEN` (env) overrides the saved token when both are present.

### 10.9 Click prog name
Invoked via `python -c`, help/usage headers show `Usage: -c …`; via the installed `atlas` script they show `Usage: atlas …`. Cosmetic only.

### 10.10 Windows CRLF
Ruff/pytest warn about LF→CRLF on checkout; harmless and unrelated to CLI behavior.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `error: Not authenticated … exit 3` | Neither `ATLAS_TOKEN` nor a saved profile. Run `atlas login` (§4). |
| `exit 3` with no friendly message on `--output json whoami` | Same, JSON error envelope is on stderr. |
| `atlas: The term 'atlas' is not recognized …` | Scripts folder not on `PATH` — add `C:\Users\Sujal\AppData\Local\Python\pythoncore-3.14-64\Scripts` (§2.3). |
| `Logged in as …` succeeded but `whoami` still exits 3 | `$env:ATLAS_TOKEN` set to something stale — it overrides the saved token (§5.1). `Remove-Item Env:ATLAS_TOKEN`. |
| `exit 4`, JSON body `"You are not an active member of the project's organization"` | Resource (e.g. a **draft** benchmark) belongs to an org you aren't active in (§10.3). **Published** benchmarks are readable by anyone. |
| `exit 5` | 404 — check the ID from §8.10. |
| `exit 6` | Backend down/unreachable/timeout. Start it (§3), check `atlas health`. |
| `exit 7` after `--password-stdin` | Empty password on stdin — pipe exactly one line, e.g. `'password123' \| atlas login --email … --password-stdin`. |
| `exit 8` `Destination already exists` | Add `--force`. |
| `exit 9` after `run watch --timeout` | The execution did not reach a terminal state within the bound. Re-run with a larger `--timeout`, or check the run separately (`run get`). |
| `exit 2` `No such option: --output` | Global option placed after the subcommand (§5.1). |
| `exit 2` + `Error: …` on unknown command / bad choice | Normal Click usage error — historically a traceback (see §10.5). |
| `TLS verification disabled for localhost` on stderr | Harmless httpx notice (§10.7). |
| `run watch` prints progress to stderr | By design; only the terminal state goes to stdout in human mode. |
| Colors look wrong in a pipe | `--no-color` disables them. |
| `ImportError: cannot import name '__version__' from 'cli' (unknown location)` | Folder-name clash when cwd is the repo root. Use the installed `atlas` script, or set `$env:PYTHONPATH="D:\atlas\cli;D:\atlas\sdk\python"`, or run from `D:\atlas\cli` (§5.1, §2.3). Not a broken install. |
| `pip`/`uv` die with `NameResolutionError` / `No such host is known` / `Failed to fetch` | No internet (PyPI DNS fails). The CLI is already installed — skip install or use the offline command §2.1. |
| `error: unrecognized subcommand 'equivalent:'` from `uv` | You pasted an *advice blockquote* (`uv equivalent: …`) into the shell as a command. Only copy lines from **code blocks**; blockquotes are explanation, not commands. |

---

## 12. Verification

Before concluding manual testing, also complete the project's standard pre-PR checklist:

- [`docs/RUNTIME_CHECKLIST.md`](../RUNTIME_CHECKLIST.md)

CLI unit/contract suites (if you want an automated sanity pass):

```powershell
# from D:\atlas\sdk\python
python -m pytest -q

# from D:\atlas\cli
python -m pytest -q
```