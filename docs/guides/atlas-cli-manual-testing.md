# Atlas CLI — Manual Testing Guide

- **Date:** 2026-08-27
- **Branch:** `feature/atlas-cli-skeleton`
- **HEAD:** `732dcc5` (`feat(cli): add report export command`)
- **Applies to:** `atlas-cli` 0.1.0 (`D:\atlas\cli`) + `atlas-sdk` 0.1.0 (`D:\atlas\sdk\python`)
- **Source of truth:** The installed/editable CLI source at `cli/cli/` (NOT the older architecture spec).
- **Audit method:** every command, option, exit code, and expected output in this guide was read from the actual implementation AND verified live against a local backend running at `http://localhost:8000` with the developer SQLite database `D:\atlas\atlas_dev.db`.

Use this document to manually exercise the CLI end-to-end. It has two audiences: a human developer, and an agent that drives `atlas` programmatically with `--output json`.

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

Both packages must be importable. They are installed **editable** so no reinstall is needed after code changes.

```powershell
# from the repo root
python -m pip install -e ./sdk/python -e ./cli
```

> uv equivalent: `uv pip install -e ./sdk/python -e ./cli` (the root `uv sync` installs the `atlas` app, not the CLI).

After install there are **two equivalent ways to run the CLI**:

```powershell
# (a) the console script (if the environment's Scripts dir is on PATH)
atlas --version

# (b) always works, no PATH setup needed (used throughout this guide)
python -c "from cli.app import main; main()" --version
```

Verification used in this guide is form (b). Both forms behave identically for success paths (`--help`, `--version`, and all commands). They differ **only** on usage errors — see §10.5.

Verify the install:

```powershell
python -c "from cli.app import main; main()" --version
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

### 3.3 Verify backend health

```powershell
Invoke-RestMethod http://localhost:8000/health            # {"status":"ok","version":"1.0.0"}
python -c "from cli.app import main; main()" health
python -c "from cli.app import main; main()" --output json health
```

---

## 4. Authentication

**The only current mechanism is a bearer token supplied via the `ATLAS_TOKEN` environment variable.** There is **no** `atlas login` command, no config-file credentials, and no PAT support (see §10.1).

### 4.1 Get a token

The backend issues JWTs from the login API. Two developer users are used in this guide (both verified live in this session): `demo@atlas.val` / `password123` (printed by `start_atlas.cmd` as the demo login) and `cli-test2@atlas.dev` / `Testtest123!` (the CLI test fixture user). Example token acquisition:

```powershell
$body = '{"email":"cli-test2@atlas.dev","password":"Testtest123!"}'
$tok  = (Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method Post `
          -ContentType "application/json" -Body $body).data.access_token
```

> **Never hard-code or echo the token.** Paste it into your shell session only. Keep the same shell session open — later sections reuse `$tok`.

### 4.2 Make it available to the CLI

```powershell
$env:ATLAS_TOKEN = "<paste token here>"
```

Every invocation reads `ATLAS_TOKEN` (see `cli/config.py`). With no token set, authenticated commands fail fast:

```powershell
python -c "from cli.app import main; main()" whoami
# error: Not authenticated — run `atlas login` or set ATLAS_TOKEN.   (see note in §10.8)
# exit code 3
```

`health` is the one exception — it works without a token (the endpoints are public).

---

## 5. Invocation patterns and global options

### 5.1 Global options — MUST come before the subcommand

All global options are defined on the top-level `atlas` group (see `cli/app.py`) and Click requires them **before** the command name. Placing them after the subcommand is a usage error.

```powershell
python -c "from cli.app import main; main()" --output json whoami        # OK
python -c "from cli.app import main; main()" --output json report list   # OK
python -c "from cli.app import main; main()" whoami --output json        # Error: No such option: --output  (exit 2)
```

| Global option | Long / short | Values | Env var | Effect |
|---|---|---|---|---|
| Output mode | `--output` / `-o` | `human` (default) \| `json` \| `quiet` (case-insensitive) | `ATLAS_OUTPUT` | Selects output rendering |
| Quiet shorthand | `--quiet` / `-q` | flag | — | Forces quiet mode (overrides `--output`) |
| Base URL | `--base-url` | URL | `ATLAS_BASE_URL` | API base (default `http://localhost:8000`) |
| Profile | `--profile` | name | `ATLAS_PROFILE` | Currently only renames the resolved profile; **no config file is read** |
| Timeout | `--timeout` | float seconds | `ATLAS_TIMEOUT` | Request timeout (default `60.0`) |
| No color | `--no-color` | flag | — | Disables ANSI colors |
| Version | `--version` / `-V` | flag | — | Prints `atlas, version 0.1.0` and exits 0 |

Precedence (highest wins): **CLI flag > environment variable > built-in default** (`cli/config.py`).

### 5.2 Bare invocations

```powershell
python -c "from cli.app import main; main()" --help
python -c "from cli.app import main; main()"            # same as --help (invoke_without_command)
python -c "from cli.app import main; main()" --version
```

Current command tree:

```text
atlas
├─ whoami
├─ health
├─ benchmark
│  ├─ list
│  ├─ get BENCHMARK_ID
│  └─ versions BENCHMARK_ID
├─ run
│  ├─ submit BENCHMARK_VERSION_ID [--target-model] [--dataset-version-id]
│  ├─ get EXECUTION_ID
│  ├─ list [--benchmark-version-id] [--status] [--limit] [--offset]
│  ├─ watch EXECUTION_ID [--interval]
│  └─ cancel EXECUTION_ID
└─ report
   ├─ list [--status] [--benchmark-id] [--benchmark-version] [--target-model] [--limit] [--offset]
   ├─ get RUN_ID
   └─ export RUN_ID [--format] [--output-file] [--include-prompt] [--include-expected-output] [--force]
```

---

## 6. Exit codes

Defined in `cli/errors.py`; commands exit via `error_exit()` (`cli/output/errors.py`).

| Code | Meaning | Typical trigger |
|---|---|---|
| 0 | Success | — |
| 1 | Unspecified / server / degraded | Backend 5xx; `health` when any probe is unreachable |
| 2 | Usage error | Unknown option, bad choice (`--format xml`), unknown command (when using the `main()` entrypoint) |
| 3 | Auth required | Missing/invalid/expired token; 401 |
| 4 | Forbidden | 403 (e.g. project/org membership) |
| 5 | Not found | 404 (e.g. unknown run/execution) |
| 6 | Network | Connection refused / DNS / timeout |
| 7 | Validation | 422 from backend |
| 8 | Conflict | `report export` destination already exists without `--force` |
| 130 | Interrupted | Ctrl-C during `run watch` |

---

## 7. Command reference

Conventions used below:
- `A=` prefix means the arg is required.
- An example "simple verification anchor" that is known to work with the current seeded DB on this machine is given per command (obtained live). IDs are shown so you can copy them, but §8 shows how to obtain them yourself from earlier commands.
- Runner used: `python -c "from cli.app import main; main()" --output json …` is abbreviated to `atlas …` below.

### 7.1 `atlas whoami`

- **API:** `GET /api/v1/auth/me`
- **Args/options:** none
- **Auth:** required (exit 3 if `ATLAS_TOKEN` unset)

```powershell
atlas whoami
atlas whoami --output json
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

> `run submit` and `run cancel` create/change backend state. Use them only if you intend to actually invoke a (eager) execution or cancel one. Everything else in this guide is read-only.

#### `atlas run submit BENCHMARK_VERSION_ID`

- **API:** `POST /api/v1/benchmarks/{id}/executions`
- **Options:** `--target-model TEXT` (default `gemini-2.5-flash`), `--dataset-version-id TEXT` (default: resolved from benchmark version)
- **Warning:** creates a real execution (QUEUED then dispatched by the eager worker).

```powershell
atlas run submit 181d1c91-15f9-43e7-866d-33809aaaedf1 --target-model mock
```

#### `atlas run get EXECUTION_ID`

- **API:** `GET /api/v1/executions/{id}`
- **Anchor (verified):** `b94248f7-f5f9-4ed8-992a-b29751b4e710`

```powershell
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710
atlas run get b94248f7-f5f9-4ed8-992a-b29751b4e710 --output json
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
- **Options:** `--interval FLOAT` (default `3.0`, must be > 0)
- Polls until status ∈ {`COMPLETED`, `FAILED`, `CANCELLED`, `TIMED_OUT`}; prints progress to stderr in human mode, final state once. Ctrl-C → exit 130. After 3 consecutive network errors → exit 1.

```powershell
atlas run watch b94248f7-f5f9-4ed8-992a-b29751b4e710 --interval 2
```

#### `atlas run cancel EXECUTION_ID`

- **API:** `POST /api/v1/executions/{id}/cancel` (sets the cooperative cancellation flag; NOT idempotent)
- Terminal-state execution → backend 409 → exit 8.

```powershell
atlas run cancel <EXECUTION_ID>
```

> Prefer a running/queued ID. Cancelling an already-terminal execution is expected to fail with 409 → exit 8.

### 7.4 `atlas benchmark …`

> **Known limitation:** all published benchmarks in the seeded DB live in project `33333333-…` under "Atlas Core Org", and no seeded test user is a member of that org. `benchmark get`/`versions` therefore return **403 (exit 4)** for every current test credential. This is verified backend behavior, not a CLI bug — see §10.4.

#### `atlas benchmark list`

- **API:** `GET /api/v1/benchmarks` (fixed `limit=50` in the CLI)
- **Args/options:** none

```powershell
atlas benchmark list
atlas benchmark list --output json
atlas --quiet benchmark list
```

Verified human output is a table (`Name`, `ID`, `State`) listing the 8 published benchmarks; empty result prints `  (no benchmarks)`. JSON keys: `items`, `total`, `limit`, `offset`, `next_cursor`.

#### `atlas benchmark get BENCHMARK_ID` / `atlas benchmark versions BENCHMARK_ID`

- **API:** `GET /api/v1/benchmarks/{id}`, `GET /api/v1/benchmarks/{id}/versions`
- **Anchor (both return 403 for test users — see note above):** `66666666-6666-6666-6666-666666666666`

```powershell
atlas benchmark get 66666666-6666-6666-6666-666666666666      # → exit 4 currently
atlas benchmark versions 66666666-6666-6666-6666-666666666666  # → exit 4 currently
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

---

## 8. End-to-end copy/paste smoke-test sequence

All commands below are **read-only** and were verified on this machine. Replace `$ATLAS_TOKEN` and `$PY` with:

```powershell
$PY = "python -c `"from cli.app import main; main()`""
# from the repo root so relative export paths are under D:\atlas
cd D:\atlas
```

### 8.1 Version and help

```powershell
& $PY --version                    # atlas, version 0.1.0   (exit 0)
& $PY --help                       # usage + commands        (exit 0)
& $PY benchmark --help
& $PY run --help
& $PY report --help
```

### 8.2 Health (no auth needed)

```powershell
& $PY health                       # human table, exit 0
& $PY health --output json         # {"api":{...},"liveness":{...},"readiness":{...},"overall":"healthy"}
& $PY --quiet health               # no output, exit 0
```

### 8.3 Human output

```powershell
& $PY whoami                       # Atlas User block        (exit 0)
& $PY benchmark list               # 8 published benchmarks  (exit 0)
& $PY run list --limit 3           # executions table        (exit 0)
& $PY report list --limit 3        # report runs table       (exit 0)
& $PY report get b94248f7-f5f9-4ed8-992a-b29751b4e710   # Report Summary, score 100.0 (exit 0)
& $PY run get b94248f7-f5f9-4ed8-992a-b29751b4e710      # Execution detail            (exit 0)
```

### 8.4 JSON output

```powershell
& $PY --output json whoami
& $PY --output json health
& $PY --output json benchmark list
& $PY --output json run list --limit 3
& $PY --output json report list --limit 3
& $PY --output json report get b94248f7-f5f9-4ed8-992a-b29751b4e710
```

Every JSON command above exits 0 and prints one JSON document to stdout. Verify pass by piping to a JSON parser if you like.

### 8.5 Quiet mode

```powershell
& $PY --quiet whoami; echo "exit=$LASTEXITCODE"        # 0
& $PY -q benchmark list; echo "exit=$LASTEXITCODE"     # 0
& $PY --quiet report export b94248f7-f5f9-4ed8-992a-b29751b4e710 --output-file smoke-quiet.json; echo "exit=$LASTEXITCODE"
```

### 8.6 Invalid / nonexistent IDs

```powershell
& $PY run get 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"        # 5
& $PY report get 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"      # 5
& $PY report export 11111111-1111-1111-1111-111111111111; echo "exit=$LASTEXITCODE"   # 5
& $PY report list --status bogus; echo "exit=$LASTEXITCODE"                           # 2 (invalid Choice)
& $PY report export x --format xml; echo "exit=$LASTEXITCODE"                         # 2 (invalid Choice)
```

### 8.7 Authentication failure

```powershell
Remove-Item Env:ATLAS_TOKEN
& $PY whoami; echo "exit=$LASTEXITCODE"                             # 3  (Not authenticated)
& $PY --output json whoami; echo "exit=$LASTEXITCODE"               # 3  (JSON error envelope on stderr)
# restore token
$env:ATLAS_TOKEN = $tok
& $PY run list; echo "exit=$LASTEXITCODE"                           # 0
```

For a live 401 (expired/garbage token), set e.g. `$env:ATLAS_TOKEN="invalid"` and re-run `whoami` → exit 3.

### 8.8 Forbidden access

```powershell
& $PY benchmark get 66666666-6666-6666-6666-666666666666; echo "exit=$LASTEXITCODE"     # 4
& $PY benchmark versions 66666666-6666-6666-6666-666666666666; echo "exit=$LASTEXITCODE" # 4
```

(Seeded published benchmarks belong to an org no seeded user belongs to — verified 403 behavior. See §10.4.)

### 8.9 Export matrix

```powershell
$RUN = b94248f7-f5f9-4ed8-992a-b29751b4e710
cd $env:TEMP

# JSON to server-provided filename in cwd
& (python -c "from cli.app import main; main()") report export $RUN            # receipt, exit 0

# CSV
& (python -c "from cli.app import main; main()") report export $RUN --format csv --output-file smoke.csv

# specified file
& (python -c "from cli.app import main; main()") report export $RUN --output-file smoke.json --output json

# include prompt + expected output
& (python -c "from cli.app import main; main()") report export $RUN --include-prompt --include-expected-output --output-file full.json

# stdout (raw bytes, byte-identical to the file version)
& (python -c "from cli.app import main; main()") report export $RUN --output-file - > raw.bin
if ((Get-FileHash raw.bin).Hash -eq (Get-FileHash smoke.json).Hash) { "stdout==file: OK" }

# overwrite refusal then --force
& (python -c "from cli.app import main; main()") report export $RUN --output-file smoke.json; echo "exit=$LASTEXITCODE"  # 8
& (python -c "from cli.app import main; main()") report export $RUN --output-file smoke.json --force; echo "exit=$LASTEXITCODE"  # 0
```

### 8.10 Recommended ID discovery

Never guess IDs — take them from an earlier JSON/list command:

```powershell
# latest run/run-id (used by report get/export and run get)
& $PY report list --limit 5 --output json            # items[].run_id
& $PY run list --limit 5 --output json               # items[].id, items[].benchmark_version_id

# benchmark version id (needed only for `run submit`, which creates an execution)
& $PY benchmark versions <BENCHMARK_ID> --output json   # items[].id
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
- `atlas login` — **does not exist.** Auth is `ATLAS_TOKEN` only.
- PAT / machine-token authentication — not implemented.
- Config files / `config.toml` / named profiles — `--profile` only changes the resolved profile name; `load_config()` reads env + flags only (`cli/config.py:7`).
- TypeScript SDK — not consulted; this guide covers the Python SDK only.
- `run submit` with a real LLM target that yields actual API costs — the default `--target-model gemini-2.5-flash` hit a real provider adapter on this box; treat submit as potentially expensive.

### 10.2 Known unrelated backend test failures
- `test_execution_backend_routing.py`: 2 failures (pre-existing, execution backend routing).
- `test_d7_reporting_async.py`: 4 errors under SQLite (`TRUNCATE` not supported — PostgreSQL-only fixture). Run the reporting async tests against PostgreSQL to confirm; on the SQLite dev DB they error, not fail logic.

### 10.3 `benchmark get`/`versions` → 403 with seeded data
All published benchmarks in the seeded SQLite DB belong to project `33333333-…` (org "Atlas Core Org"); no seeded user holds membership there, so `benchmark get`/`versions` → exit 4 for `demo@atlas.val` and `cli-test2@atlas.dev` alike. To see a successful `benchmark get`, use a benchmark whose project belongs to an org you are an ACTIVE member of.

### 10.4 `run get` on `b94248f7` reports `RUNNING` while the report is `COMPLETED`
The execution detail endpoint sources the separate `ee_executions` table (`status RUNNING`, progress `0/1`), while `report get` on the same ID returns `COMPLETED` / score 100.0. Backend data-source discrepancy — the CLI faithfully renders each endpoint.

### 10.5 `atlas.exe` usage-error exit codes differ from `python -c` invocation
The console-script entrypoint calls `main(standalone_mode=False)`, so Click usage errors (unknown command/option, bad Choice) raise uncaught `click.UsageError` → traceback + exit 1. The `python -c "from cli.app import main; main()"` form used here runs `standalone_mode=True`, producing clean `Usage:` output and exit 2. Use the `python -c` form while testing exit-code expectations.
### 10.6 Unhandled local I/O exceptions

`report export` propagates a raw `FileNotFoundError`/`PermissionError` if the destination can't be opened (only the overwrite-refusal path yields the clean exit 8). Expect an unhandled traceback and a non-zero exit code in that case.

### 10.7 httpx prints `TLS verification disabled for localhost target` to stderr
This INFO line appears once per process for `localhost` targets. Harmless; it goes to stderr and does not affect stdout/exit codes. It is why `2>$null` appears in this guide's examples.

### 10.8 Stale `atlas login` reference
`whoami`'s no-token error says `run `atlas login` or set ATLAS_TOKEN` (`cli/commands/auth.py:34`) but `atlas login` does not exist. Treat the message as aspirational; use `ATLAS_TOKEN`.

### 10.9 Click prog name
Invoked via `python -c`, help/usage headers show `Usage: -c …`; via the installed `atlas` script they show `Usage: atlas …`. Cosmetic only.

### 10.10 Windows CRLF
Ruff/pytest warn about LF→CRLF on checkout; harmless and unrelated to CLI behavior.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `error: Not authenticated … exit 3` | `ATLAS_TOKEN` unset. Set it (§4). |
| `exit 3` with no friendly message on `whoami --output json` | Same, JSON error envelope is on stderr. |
| `exit 4`, JSON body `"You are not an active member of the project's organization"` | Resource belongs to an org you aren't active in (§10.3). |
| `exit 5` | 404 — check the ID from §8.10. |
| `exit 6` | Backend down/unreachable/timeout. Start it (§3), check `atlas health`. |
| `exit 8` `Destination already exists` | Add `--force`. |
| `exit 2` `No such option: --output` | Global option placed after the subcommand (§5.1). |
| `exit 1` + traceback on unknown command (installed `atlas`) | §10.5 `standalone_mode=False` behavior. |
| `TLS verification disabled for localhost` on stderr | Harmless httpx notice (§10.7). |
| Empty JSON output + exit 0 for benchmark get | Not reproducible; benchmark get currently 403s (§10.3). |
| `run watch` prints progress to stderr | By design; only the terminal state goes to stdout in human mode. |
| Colors look wrong in a pipe | `--no-color` disables them. |

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