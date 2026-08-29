# Atlas CLI v2 — Implementation Plan (Agent-Loop Readiness)

> **Status:** Plan only. **No code changed.**
> **Branch:** `feature/atlas-cli-v2` (HEAD `28c0749`; this doc becomes the next commit).
> **Source inputs:** `docs/guides/atlas-cli-v2-workflow-audit.md` (facts) + `docs/guides/atlas-cli-v2-architecture-investigation.md` (design decisions).

## Mandates (from the user)

1. Start from `28c0749` on `feature/atlas-cli-v2`.
2. **Tests-first** for every change (red test → implementation → green).
3. **Separate logical commits** (one per slice below).
4. **Git commits only — absolutely no push, merge, or PR.**
5. Backend contract fixes allowed *in this repo* where required; never paper over them in the CLI.
6. Preserve v1 behavior unless a deliberate v2 change requires otherwise (each deliberate change is flagged).
7. Verify against the **live backend**, not just mocks.
8. Do **not** turn v2 into an API-wrapper kitchen sink.

## Scope guards (what v2 deliberately does NOT do)

- No new command groups; no `atlas agent`; no agent mode.
- No renaming existing JSON fields (back-compat) — new fields only.
- No idempotency-key header work, no billing integration, no `compare`, no profiles overhaul.
- Existing exit codes keep their meaning. One **new** exit code (9) for the one genuinely-new condition (watch timeout bound).
- Backend changes limited to the two contract fixes (execution authority; published-benchmark read + real submit authz).

## Test/verification baseline (used every slice)

| Concern | Command |
|---|---|
| CLI unit tests (322 v1) | `uv run --directory cli pytest -q` |
| SDK unit tests (165 v1) | `uv run --directory sdk/python pytest -q` |
| Backend tests (affected files) | `uv run pytest tests/backend/test_<file>.py -q` |
| Root lint | `uv run ruff check <changed packages>` |
| Root typecheck | `uv run mypy <changed packages>` (as exercised in v1) |
| Live API smoke | `curl.exe -s -m 10 http://localhost:8000/health` |

**Live-env prerequisites:** backend up on `:8000` (currently PID 3516; restart recipe in `docs/guides/atlas-cli-manual-testing.md` §3.2 — never run `start_atlas.cmd`) and `atlas login` present (demo@atlas.val). Shell note for your manual runs: capture `$LASTEXITCODE` immediately after the call; avoid `2>&1` in PowerShell (clobbers it) — use `2>$null` for quiet runs or `cmd /c "... 2>err.txt"` when you need to inspect stderr.

---

## Slice 1 — Execution authority / state consistency (P0, backend)

**Goal:** `GET /api/v1/executions/{id}` (and therefore `atlas run get`) returns the same truthful execution that reports/dashboard/export already show. Engine internals stop being the API's execution state.

**Root cause (verified):** `apps/backend/routers/executions.py:199-213` → `ExecutionApplicationService.get_execution` reads `ee_executions` (`packages/execution_engine/persistence/repository.py:53-58`), the row only `ExecutionWorker` syncs; every other surface reads `executions` (`dashboard.py`, `reporting_repo.py`).

### Tests first (`tests/backend/test_api_executions.py` + new `tests/backend/test_execution_authority.py`)
Append a small isolated TestClient suite (pattern: `tests/api/test_execution_contract.py` dependency-override fixtures):
1. **`ee` row drifted, `executions` row COMPLETED** → `GET /executions/{id}` returns `status == "COMPLETED"` (the authority), not "RUNNING". Wire `get_execution_service` override to a fake returning an engine object, and override the authoritative read path to return the `executions` row.
2. Timestamps: authoritative response carries `started_at`/`completed_at` when the `executions` row has them (currently `null` forever for the drift case).
3. Progress: `completed_items`/`total_items` come from the authoritative row.
4. Existing tests keep passing (`test_create_execution`, `test_list_executions`, `tests/api/test_execution_contract.py`).

### Implementation
- In `get_execution` route, resolve the authoritative row (the `executions` table — same repo the dashboard uses) and render `ExecutionResponse` from it: status, `queued_at/started_at/completed_at`, `total_items/completed_items`. Keep engine `attempts` only as auxiliary context if cheap; **status/timestamps/progress are authoritative-row-only**. Simplest correct shape: the route consults `ExecutionApplicationService` only for submission/cancel, and a tiny query/repo function for the unified read.
- Do NOT touch the CLI for this slice: `atlas run get` simply starts reporting correctly (behavior change on data, not on interface).
- Also correct the common-sense symptom: a stuck engine aggregated row must never show `RUNNING` forever once the authoritative row is terminal — the unified read decides.

### Deliberate v2 changes
- None to the CLI surface. Backend response semantics: `GET /executions/{id}` is now the evaluation's truth, matching `report`/`dashboard`.

### Commit
`fix(backend): make run get read the authoritative execution row (status/timestamps/progress)`

### Verify
```
uv run pytest tests/backend/test_api_executions.py tests/backend/test_execution_authority.py tests/api/test_execution_contract.py -q
# live:
atlas run get bf6c70b3-0f23-451d-9c1d-1e84f41bb63d --output json
atlas report get bf6c70b3-0f23-451d-9c1d-1e84f41bb63d --output json
atlas run submit 181d1c91-15f9-43e7-866d-33809aaaedf1 --target-model mock
atlas run get <new-run-id> --output json
```
Expect: old stuck run now reports COMPLETED everywhere; a fresh `mock` run reports COMPLETED (score nullable) everywhere, with `started_at`/`completed_at` populated.

---

## Slice 2 — Published benchmark/version discovery (P0, backend)

**Goal:** any authenticated user can read a **published** benchmark and its versions, so `atlas benchmark versions` works and the chain `benchmark → versions → run submit` is complete. Unpublished/draft stays org-gated, and submit gets **real** authorization.

**Root cause (verified):** `get_benchmark`/`list_benchmark_versions` 403 for catalog reads (`apps/backend/routers/benchmarks.py:106-118,216-227`) because `project_authz.authorize_project_access` has no published exemption, while submit passes through a no-op `require_permission` (`apps/backend/authz.py:89-93`) → catalog read severed from execution; also `dispatch-targets` (`routers/executions.py:155-196`) enumerates **all** versions incl. drafts behind the stub.

### Tests first (`tests/backend/test_benchmark_discovery.py` + extend `tests/backend/test_api_authz.py`)
1. Published benchmark + non-member user → `GET /benchmarks/{id}` 200; `GET /benchmarks/{id}/versions` 200 with version rows containing version IDs.
2. Draft benchmark + non-member → both 403 (unchanged).
3. Org-member on their own org's draft → 200 (unchanged for members).
4. Submit: non-member submits against a **published** version → works; against a **draft** version → 403 (new real gate).
5. `dispatch-targets` lists only **published** versions (or is removed from the authz gap list — decision: gate it to published + org draft).

### Implementation
- In the read path, short-circuit when `benchmark.status == "published"` (published ⇒ readable by any authenticated user). Keep membership path for draft/private.
- Make `require_permission("benchmark:execute")` real for the version the submit targets: allow if parent benchmark published, else require org membership.
- Apply the same published rule to `dispatch-targets` enumeration.

### Commit
`fix(backend): published benchmarks readable catalog; real submit authorization per version`

### Verify
```
uv run pytest tests/backend/test_benchmark_discovery.py tests/backend/test_api_authz.py tests/backend/test_api_benchmarks.py -q
# live (version ID from activity or leaderboard --history):
atlas benchmark get 181d1c91-15f9-43e7-866d-33809aaaedf1 --output json
atlas benchmark versions 181d1c91-15f9-43e7-866d-33809aaaedf1 --output json
atlas run submit <version-id> --target-model mock
```
Expect: `get` and `versions` now exit 0 (were exit 4); versions return `id` fields that feed submit directly.

---

## Slice 3 — `run watch --timeout` (P0, CLI)

**Goal:** a deterministic cap on waiting. `watch` exits with a documented code and (in JSON mode) the last observed non-terminal state, so an agent can bound total time and re-poll.

**Design (from investigation §3):**
- `atlas run watch <execution-id> [--timeout SECONDS] [--interval FLOAT]` — default `--timeout 0` becomes **unbounded currently; recommended default 0 is preserved for back-compat, and the option must be present** so agents bound it. (Decision: keep default = 0 = v1 behavior; document it.)
- New exit code `9 = WATCH_TIMEOUT` added to `cli/cli/errors.py` (next free integer; existing 0,1,2,3,4,5,6,7,8,130 unchanged).
- On bound expiry with no terminal state:
  - JSON: emit the last `execution.model_dump(mode="json")` to stdout (those fields reflect Slice 1's truthful row), exit 9.
  - Human: `timed out after <N>s — status RUNNING (0/1 items); re-run with a larger --timeout`.
- `_poll_execution` (`cli/cli/commands/run.py:311-354`) gains a wall-clock deadline; the per-poll SD timeouts and 3-consecutive-failure cap are untouched.

### Tests first (`cli/tests/test_run.py`, `cli/tests/test_exit_codes.py`)
1. Fake client whose `get_execution` stays QUEUED → `--timeout 5 --interval 1` exits `9`; JSON output is the last non-terminal `ExecutionResponse` dict; help hint text present in human mode.
2. Completion within bound → exits 0 (unchanged) with terminal render.
3. `ExitCode.WATCH_TIMEOUT == 9` maps through `errors.py`; exit-code table doc updated.
4. Golden/help snapshot (`cli/tests/test_golden.py`, `test_cli_parsing.py`) updated for the new option.
5. Network-failure cap path still exits 1 (regression guard).

### Deliberate v2 changes
- New option (`--timeout`) + new documented exit code 9; default behavior identical to v1.

### Commit
`feat(cli): bound run watch with --timeout (exit 9, last-state JSON on expiry)`

### Verify
```
uv run --directory cli pytest -q
# live — a competing real run works; for deterministic demo use a long-queued run or tight bound:
atlas run watch <some-id> --timeout 5 --interval 1 --output json
echo "exit=$LASTEXITCODE"   # expect 9
atlas run watch <completed-id> --timeout 5 --output json   # expect 0
```

---

## Slice 4 — Safe `run submit` / `--preview` (P1, CLI)

**Goal:** no silent paying default; a deterministic, cost-free preflight.

**Design (from investigation §4):**
- `--target-model` becomes **required** (Remove the `gemini-2.5-flash` default at `cli/cli/commands/run.py:56`.) This is the deliberate v2 change: "forgot the model" can never silently spend money. Update help + Example.
- Add `--preview`: resolve benchmark-version → dataset-version + adapter (same mapping the backend uses: `mock|mocked` → MockModelAdapter, else RealModelAdapter — mirrored at `cli/` for the *plan*, never to decide truth), print a machine-readable plan (version, dataset_version_id, target_model, adapter kind, estimated nothing/“no cost preflight”), **no POST**, exit 0. Uses existing read-only GETs only (Slice 2 makes them available).
- Keep POST retry-free (Slice 5).

### Tests first (`cli/tests/test_run.py`)
1. `run submit` without `--target-model` → usage error, exit 2, stderr `Error: ...`; golden/help updated.
2. `run submit --target-model mock` still exits 0 with current render (progress-bearing fields unaffected).
3. `--preview` with valid version (fake `benchmark.versions` read) prints plan JSON, never calls `submit_execution` (assert mock not invoked), exit 0.
4. `--preview` with unknown version → exit 5 via SDK NotFound (unchanged path).

### Deliberate v2 changes
- `--target-model` now required; new `--preview` flag. Everything else byte-identical.

### Commit
`feat(cli): require target model for run submit; add cost-free --preview`

### Verify
```
uv run --directory cli pytest -q
# live:
atlas run submit 181d1c91-15f9-43e7-866d-33809aaaedf1 --output json          # exit 2 usage
atlas run submit 181d1c91-15f9-43e7-866d-33809aaaedf1 --preview --output json  # exit 0, plan, NO run created
atlas run submit 181d1c91-15f9-43e7-866d-33809aaaedf1 --target-model mock --output json  # exit 0
```

---

## Slice 5 — Expose existing SDK retry capability (P1, CLI)

**Goal:** surface what the SDK already has (`max_retries`, `client.py:103`) without re-inventing retry.

**Design:** add global `--retries N` (env `ATLAS_RETRIES`), plumbed into `AtlasConfig` and into a new shared client builder so all 12 inline `AtlasClient(...)` constructions (`cli/cli/commands/*.py`) pass it. POST stays non-retried (idempotency) — this is SDK behavior, unchanged.

### Tests first
1. `cli/tests/test_config.py`: `--retries 0/3/9` and `ATLAS_RETRIES` precedence; invalid (non-int, negative) → usage error exit 2.
2. `cli/tests/test_cli_parsing.py`: flag exists and is forwarded.
3. `cli/tests/test_health.py` (or new `cli/tests/test_client_builder.py`): builder passes `max_retries` to `AtlasClient`; a mock client records the value for `--retries 0` vs default 3.
4. SDK already covered (`sdk/python/tests/test_client.py` uses `pytest-httpx` for 429/5xx + transport retry) — no SDK change.

### Implementation
- `cli/cli/client.py`: `build_client(cfg, *, token_supplier=None, timeout=...)` returns `AtlasClient(base_url=cfg.base_url, token_supplier=..., timeout=..., max_retries=cfg.retries)`; migrate the 12 sites (mechanical; watch keeps its `timeout=5.0` override via parameter).
- `cli/cli/app.py`, `cli/cli/config.py`: add `retries` (int, default 3).

### Commit
`feat(cli): expose SDK retry count via global --retries (config.plumbed, POST still non-idempotent)`

### Verify
```
uv run --directory cli pytest -q
# live:
atlas --retries 0 health --output json; echo "exit=$LASTEXITCODE"   # works; SDK won't retry
atlas --retries -1 health; echo "exit=$LASTEXITCODE"                 # exit 2 usage
atlas --retries 3 run get <id> --output json                         # healthy round-trip
```

---

## Slice 6 — `--fields` projection + `--json-schema` (P1/P2, CLI, "where justified")

**Goal:** tame heavy/heterogeneous JSON (`dashboard`, `activity`) and let agents select fields without learning shapes by heart — **no separate agent mode**.

**Design:**
- `cli/cli/output/project.py`: `project(data, fields)` — comma-separated dot-paths (`id,status,benchmark_version_id`); arrays map element-wise; prefix semantics explicit. Unknown field → CLI usage error (exit 2) for determinism. No `--fields` ⇒ output byte-identical (regression-guarded by `test_golden`).
- Justified command set (heavy or heterogeneous or discovery-critical): `dashboard`, `activity`, `run get`, `run list`, `report get`, `report summary`, `leaderboard --history`, `leaderboard model`, `leaderboard benchmark`, `benchmark list/get/versions`.
- `--json-schema` on the same set: prints the JSON Schema of that command's SDK response model (from the pydantic model `model_json_schema()`), exit 0 — the self-description that kills P9/P10 drift without renaming fields.

### Tests first
1. `cli/tests/test_output.py`: `project` unit cases (flat, nested, arrays, missing key, unknown field → usage error, empty), full-shape passthrough with no `--fields`.
2. `cli/tests/test_output_contract.py`: `dashboard --fields id,status` on fixture prunes exactly; `report get --json-schema` emits a JSON Schema document containing the model's properties (e.g. `status`, `literal` enum values preserved); `activity --fields` works on heterogeneous items.
3. `cli/tests/test_golden.py`: `--help` shows both flags on the justified commands.

### Deliberate v2 changes
- New flags only; no default-output change; field names untouched.

### Commit
`feat(cli): add --fields projection and --json-schema to justified outputs`

### Verify
```
uv run --directory cli pytest -q
# live:
atlas dashboard --fields id,status --output json
atlas activity --type executions --fields id,benchmark_name,status --output json
atlas report get bf6c70b3-... --json-schema --output json | Out-Null
atlas dashboard --fields no.such.field --output json; echo "exit=$LASTEXITCODE"  # exit 2
atlas dashboard --output json   # unchanged vs v1 shape (spot check)
```

---

## Slice 7 — Remaining v2 features (P2; decision point)

Not planned in this round. Candidates held back, ranked, each gated on real agent workflows:
1. `run list`/`report list` **pagination + filters** (biggest remaining agent ergonomics gap — do first if any P2s are approved).
2. Profiles/config polish (profiles exist; only small ergonomic fixes, no migration).
3. `compare` — only if a concrete workflow needs side-by-side; not otherwise.
4. Anything requiring new backend endpoints beyond the two contract fixes — treat as a new proposal, not part of this plan.

**Recommended posture:** close out Slices 1–6, re-run the full v1 audit-checklist, then re-evaluate 7.x against actual agent task traces. Nothing here without your sign-off.

---

## Commit order (all local, on `feature/atlas-cli-v2`)

1. `28c0749` (existing) — this plan: `docs(plan): v2 implementation plan (tests-first, slices 1-7)`
2. `fix(backend): make run get read the authoritative execution row ...`
3. `fix(backend): published benchmarks readable catalog; real submit authorization ...`
4. `feat(cli): bound run watch with --timeout (exit 9, last-state JSON on expiry)`
5. `feat(cli): require target model for run submit; add cost-free --preview`
6. `feat(cli): expose SDK retry count via global --retries ...`
7. `feat(cli): add --fields projection and --json-schema to justified outputs`

Each commit: tests green in its package + affected backend tests + ruff/mypy clean + live-check done, per the baseline table. Never `git push`/`git merge`/PR. After the last commit, update this plan's status and report.

## Done-criteria for the sprint (minimal, not kitchen-sink)
- `run get` == `report` == `dashboard` for the same run (live, incl. the previously-stuck `bf6c70b3`)…
- `benchmark get/versions` reachable for published benchmarks; submit is real-authz; draft execution blocked for outsiders.
- `watch` bounded (`--timeout`, exit 9, last-state JSON); `submit` requires an explicit model + offers `--preview`; `--retries` plumbed; `--fields`/`--json-schema` on justified outputs.
- Full CLI + SDK + affected backend suites green; all commits local; no push.