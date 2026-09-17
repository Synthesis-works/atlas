# Atlas CLI v2 — Architecture Investigation (Agent-Loop Readiness)

> **Status:** Decision/design input only. **No code changed.**
> **Branch:** `feature/atlas-cli-v2` (from v1 freeze `0b99d6b`; audit doc committed as `e2e6905`)
> **Date:** 2026-08-29
> **Scope:** Backend contracts (`apps/backend`, `packages/*`) + CLI/SDK (`cli/`, `sdk/python`), inspected from source with live verification where it matters. Follows the workflow audit (`docs/guides/atlas-cli-v2-workflow-audit.md`), which established the real v2 goal: **make the CLI agent-operable end-to-end, not "add more commands".**

## Guiding principles (confirmed)

1. **One interface.** Human and agent consume the *same* `atlas` commands, JSON, and exit codes. No `atlas agent` group, no separate agent mode. v2 makes the existing interface *more deterministic and composable*.
2. **No client-side masking.** Where the backend is inconsistent, the fix belongs in the backend contract — the CLI must not paper over it with clever retries/reinterpretation.
3. **Local-commits-only** until the user says push.

---

## 0. Executive summary

| # | Topic | Current state | Primary root cause | Recommended fix location |
|---|---|---|---|---|
| 1 | Authoritative execution state | `run get` says RUNNING while reports/dashboard/export say COMPLETED for one run | **Two execution tables**: `ee_executions` (read by `run get`) vs `executions` (read by everything else); only `ExecutionWorker` syncs both | **Backend** — make `executions` the single outward authority; stop exposing the engine's internal aggregate as the run's API state |
| 2 | Benchmark/version discovery | `benchmark list` shows published, but `get`/`versions` 403 while `run submit` works | List = global published catalog (by design); `get`/`versions` re-impose an old org-membership check with **no published exemption**; `run submit` keyed by version-id with a **no-op authz stub** | **Backend** — publish-read contract: published benchmarks readable (get + versions) by any authenticated user |
| 3 | Bounded watch | `run watch` polls forever; no `--timeout` | CLI loop is `while True`; per-poll timeout (5 s) and a 3-consecutive-network-failure cap exist, but no total bound | **CLI/SDK** — add `--timeout` (wall-clock) with a defined terminal `TIMEOUT` outcome + deterministic exit |
| 4 | Safe submit defaults | CLI default target `gemini-2.5-flash` (paid provider) | CLI sets its own default that overrides the backend's cheaper default; no preflight | **CLI** (contract change) — no silent paid default; explicit target or clearly-safe default; add `--preview` |
| 5 | Retry semantics | SDK already retries GET/HEAD (3×, 429/5xx/transport); POST never retried; CLI exposes no knobs | Retry exists but is not surfaced/controllable | **CLI** — global `--retries` (maps to SDK `max_retries`); never retry non-idempotent calls |
| 6 | Machine-readable output | JSON on stdout + error envelope on stderr is solid; heavy dashboard payload; heterogeneous activity shapes; field-name drift | Per-endpoint serializers diverge | **CLI (+SDK)** — uniform `--fields`, `--json-schema` self-description, field naming cleanup |

**Sequencing:** Backend contract changes (1, 2) are *prerequisites* for the CLI to become trustworthy; CLI-side work (3, 4, 5, 6) can proceed in parallel but must consume whatever contract lands. Because this monorepo contains both backend and CLI, the intended order is: land + test the backend contract first (its own commits), then reshape the CLI consume path — never adapt the CLI to a bug.

---

## 1. Authoritative execution lifecycle

### Evidence (source)
- **Two execution tables exist and are both real:**
  - `executions` — `packages/database/atlas_db/models/execution.py:98-147` (status ENUM `execution_status`, `project_id`, `benchmark_version_id`, `dataset_version_id`, `submitted_by_id`, `queued_at/started_at/completed_at`, `total_items/completed_items`, `execution_config`).
  - `ee_executions` — `packages/execution_engine/persistence/models.py:13-30` (same status ENUM; **no** `started_at/completed_at` columns; `project_id` default is a random uuid4, not a real project; default `target_model="test-model"`).
- **Submit writes both:** `apps/backend/routers/executions.py:70-151` → `ExecutionApplicationService.submit_execution` (`packages/execution_engine/application/execution_app_service.py:36-92`) saves the domain aggregate to `ee_executions` (line 62) *and* a hand-built `DBExecution` row to `executions` (lines 64-84). Both start `QUEUED`.
- **`run get` reads the ee table only:** `get_execution` (`routers/executions.py:199-213`) → `SqlAlchemyExecutionRepository.get` → `ExecutionModel(@__tablename__ = "ee_executions")` (`packages/execution_engine/persistence/repository.py:53-58`, `persistence/models.py:13-14`). Its `attempts` array is the engine's `execution_attempts`/`execution_leases` (`routers/executions.py:48-66`).
- **Everything else reads `executions`:**
  - `run list` and dashboard: `apps/backend/routers/dashboard.py:78-233` builds everything (`active_executions`, `recent_verified_runs`, `running_jobs`, summary counts, `progress`) from `Execution` (`dashboard.py:16`, item builder `:47-60`).
  - `report get`/`list`: `services/report/repositories/reporting_repo.py:7` — `AtlasRun = Execution`; `evaluation_status` is computed from `executions.status` (`services/report/services/queries.py:26-50`). `reports.report_versions.execution_id` FK targets `executions.id` (`atlas_db/models/reporting.py:27-28`).
  - `report export` payload's embedded `execution.status` is likewise this row.
- **The only sync point is the worker:** `ExecutionWorker.process` loads **both** rows and `update_both_status(...)` (`apps/backend/worker/execution_worker.py:48-73`) — QUEUED→RUNNING at line 85, →COMPLETED at lines 119-121; `started_at` set only here (`:63-64`). If the worker path never runs (e.g., `EXECUTION_BACKEND=disabled`, or current local env where the eager dispatch stalls), the ee row stays `QUEUED`/`RUNNING` while `executions` can still be written independently by `ExecutionRunner.run` (`apps/backend/worker/execution_runner.py:203-205`).
- **Worker docstring states the intended single lifecycle:** "QUEUED -> RUNNING -> COMPLETED/FAILED/CANCELLED/TIMED_OUT" (`execution_worker.py:23`).

### Diagnosis
There is exactly **one intended truth**: the run's outward status is meant to be a single value, kept in sync across both tables by `ExecutionWorker`. The API, however, leaks the *internal engine aggregate* (`ee_executions`) through `GET /api/v1/executions/{id}`, and that row is the one that drifts. The live audit run `bf6c70b3` reproduced it exactly: `run get/list/watch` = RUNNING; `report list/get` + `report export` + `dashboard` = COMPLETED.

This is **one bug with two candidate fixes**, and v2 must choose deliberately:

- **Option A (recommended) — `executions` is authoritative; the API exposes it.** Change `GET /api/v1/executions/{id}` (and anything else surfacing `ee_executions` reachable state) to read the same `executions` row that reports/dashboard use, or map the engine aggregate onto the unified response. `ee_executions` + attempts/leases remain internal scheduler machinery, not API-visible. Outcome: `run get` == `report get` == dashboard always.
- **Option B — distinct concepts, distinct names.** If the engine genuinely has two stages (dispatch state vs evaluation outcome), the contract should expose *two clearly-named fields* (e.g. `dispatch_status` + `evaluation_status`) so an agent never has to guess which name to trust. This only makes sense if the two-table split is deliberate, which the sync worker + single `ExecutionStatus` enum argue against.

**Decision for v2:** Option A. Pair it with fixing the leftover symptoms that surface via the unified row: `started_at`/`completed_at` plumbed correctly on the authoritative row, and the daemon ensuring a terminal state is eventually written (see §3 re: watch/timeouts). **No CLI reinterpretation of statuses.**

---

## 2. Benchmark/version discovery & authorization

### Evidence (source)
- **List is deliberately global-and-published:** `GET /api/v1/benchmarks` (`apps/backend/routers/benchmarks.py:84-96`) requires only `require_authenticated` + a comment "Global discovery endpoint (requires auth but no specific project role)"; service layer forces `status="published"` (`apps/backend/services/benchmarks.py:119-133`). Response `BenchmarkRead` has **no version id** (`apps/backend/schemas/benchmarks.py:39-46`: `id`, `project_id`, `state`, `name`).
- **`get`/`versions` run an unconditional org check with no published exemption:** `get_benchmark` and `list_benchmark_versions` both call `project_authz.authorize_project_access(...)` (`apps/backend/routers/benchmarks.py:106-118` and `:216-227`), which 403s unless the user is an ACTIVE member of `benchmark.project_id`'s org (`apps/backend/authz.py:59-82`). `visibility` is stored on the model (`authoring.py:70`, seeded `"public"`) but **never consulted** for read auth.
- **Version `state` is inherited, not stored:** `BenchmarkVersion` has no state column; `BenchmarkVersionRead.state = benchmark.status` (`apps/backend/services/benchmarks.py:284-306`). "Published version" ⇒ parent benchmark `status="published"`.
- **Submit is version-id-keyed and effectively unauthed:** `POST /api/v1/benchmarks/{id}/executions` takes a `benchmark_version_id`, resolves the version, and its only auth is `require_permission("benchmark:execute")` — a **no-op stub** that just returns the JWT sub (`apps/backend/authz.py:89-93`). No org check at all (`routers/executions.py:75-151`). That's why submit works while `get`/`versions` 403.
- **Seeds:** published benchmarks live in project `33333333-…` under org `11111111-…` (`seed_demo.py:48-81`), while the demo user is a member of a *different* org (`packages/database/scripts/seed.py:32,50-68`) → org mismatch is "correct" for membership but blocks what the product treats as public catalog.

### Diagnosis
The product intent is already visible in the code: **published benchmarks are a globally discoverable catalog** (list + `history.py` docstring "most recently published benchmarks globally … status='published'"). But the resource-read endpoints (`get`, `versions`) never got the "published ⇒ readable" branch, and the execution entry point took a *different* (version-id) shortcut that skips auth entirely. Result: discovery is severed from execution — the exact P2 blocker from the audit.

### Recommended contract (backend-first)
Establish and implement the rule consistently, in one place:

> **"Published" benchmarks are catalog objects. Any authenticated user may: list published benchmarks, read a published benchmark, read its versions (and thus version IDs), and submit executions against a published version.** Draft/private benchmarks and all mutation remain governed by the existing org-membership authorization.

Concretely:
1. In the READ path (`get_benchmark`, `list_benchmark_versions`), short-circuit the org check when `benchmark.status == "published"` (and, if `visibility` is meant to matter, require `visibility == "public"`).
2. Optionally extend `BenchmarkRead`/list to surface the current published version (or add a lightweight `published_version` summary) so agents don't need a second round-trip — but with (1), `versions` gives them full IDs anyway.
3. Keep submit's version-id entry, but **give it real authorization**: it should validate "version's benchmark is published **or** caller is org member", so unpublished-benchmark execution is impossible for outsiders (closing the current no-op-stub hole — today any authenticated user can submit against *draft* version ids too).
4. `require_permission` stub: either implement it over the new rule or remove it and make the two authz paths share one helper.

The CLI needs **no workaround** for this; the backend fix alone unblocks `atlas benchmark versions` → `run submit` for the demo/seeded catalog. CLI-visible improvement after the fix: `benchmark versions` returns data (403→200), so the full agent chain `benchmark → versions → submit` works with existing commands.

---

## 3. Bounded `run watch`

### Evidence (source)
- `run watch` (`cli/cli/commands/run.py:272-308`): options `--interval FLOAT` (default 3.0); constructs a client with `timeout=5.0` (per-poll total) and calls `_poll_execution`.
- `_poll_execution` (run.py:311-353): `while True` loop — **no total wall-clock bound**. Per-poll client timeout 5 s; `_TERMINAL_STATES = {COMPLETED, FAILED, CANCELLED, TIMED_OUT}` (run.py:28); consecutive `NetworkError` cap `_MAX_CONSECUTIVE_FAILURES = 3` (run.py:30) exits `UNSPECIFIED`; `KeyboardInterrupt` → exit 130 (run.py:305-306).
- SDK GET retry (see §5) partially cushions transient network failures during poll, but neither SDK retries nor the consecutive-failure cap bound total duration.

### Recommended contract
Give the agent a deterministic way to *never wait forever*:

```
atlas run watch <execution-id> [--timeout SECONDS] [--interval FLOAT] [--exit-on TIMEOUT]
```

- `--timeout` = maximum wall-clock seconds to poll before giving up (default, say, 0 = current behavior, or a safe default like 300 s — decide during design; recommendation: **default 0 is dangerous, pick a sane default** or require explicit `--timeout`).
- On timeout the command must be **non-ambiguous and machine-parseable**:
  - JSON mode → print the last observed execution state (non-terminal) as a document and exit with a **documented** code. Recommendation: introduce a distinct exit code for "watch exhausted its bound" (e.g. `9`/`WATCH_TIMEOUT`) rather than overloading `1`, so an agent can distinguish "poll ended at bound, run still QUEUED/RUNNING" from a real failure — and document it in the exit-code table. (This respects the "same exit codes" principle: we add a *new* exit code for a *new* condition; we never renumber existing ones.)
  - Human mode → "timed out after Ns — status RUNNING, 0/1 items; re-run with --timeout to keep polling."
- `--exit-on TIMEOUT`: optional allow-list so an agent can watch "until RUNNING (e.g. dispatched)" rather than only terminal states — cheap to add, high value; or defer if scope-creepy.
- SDK affordance: `watch` currently polls `get_execution`. Once §1 lands (authoritative row), watch/generic "wait" primitives should poll the same authoritative endpoint.

---

## 4. Safe submission defaults

### Evidence (source)
- CLI: `--target-model` default `"gemini-2.5-flash"` (`cli/cli/commands/run.py:56-57`), **help text even advertises it**. Passed straight to `POST /api/v1/benchmarks/{id}/executions` which resolves adapters at execution time (`apps/backend/adapters/real.py:28`; `Factory` maps `mock|mocked` → `MockModelAdapter`, everything else → `RealModelAdapter`, `apps/backend/adapters/factory.py:6-21`).
- The **backend's own default is `groq/llama-3.1-8b-instant`** (`routers/executions.py:107`) — also an external provider. So both defaults are real-provider.
- Submit is a **state-creating POST with no preflight/dry-run** and no cost estimate surfaced.

### Recommended contract
- **No silent paying default.** Two acceptable designs (pick one in the v2 plan):
  a. `--target-model` becomes **required** (no default), with help listing available adapters; or
  b. Default becomes an obviously-free/safe adapter (`mock`), and any real-provider target requires an explicit `--target-model`, so "forgot to say what model" can never spend money.
- Add **`run submit --preview`**: resolve benchmark-version → dataset-version → adapter/model + estimated cost **without creating an execution**, printing a machine-readable plan (exit 0) that the agent can approve and then submit. If the backend lacks a preview endpoint, add a small read-only route (backend commit) rather than client-side estimation.
- Keep idempotency in mind for POST retry (see §5): never auto-retry submit; an agent that "didn't see the response" must re-check with `run list`/`run get` rather than resubmit blindly.

---

## 5. Retry semantics

### Correction to the audit
The workflow audit's §5/P7 said "no built-in retry". Source review **overturns that**: the SDK already retries idempotent reads.

### Evidence (source)
- `AtlasClient` (`sdk/python/atlas_sdk/client.py`): `_MAX_RETRIES = 3`, backoff `0.5 * 2^attempt` (`:56-57`), retryable statuses `{429, 502, 503, 504}` + `>= 500` (`:58-63`), plus `httpx.TransportError` handling (`:192-194`). `_get` calls `_do_request(..., retry=True)` (`:272-273`); `_post` uses `retry=False` (`:281-282`) — **POST is intentionally never retried** (idempotency).
- CLI constructs clients with `base_url/token_supplier/timeout` only (e.g. `cli/cli/commands/auth.py:53`, all others similar) — `max_retries` is **not plumbed/exposed**.
- `run watch` additionally self-bounds consecutive network failures to 3 (`run.py:30,341-353`).

### Recommended contract
- Add a global `--retries N` (maps to `AtlasClient(max_retries=N)`; default keeps SDK's 3). Applies to idempotent calls only.
- **Never retry non-idempotent requests (submit)**; document "retry-safe to re-poll, not to replay POSTs". If a future workflow needs safe replay, add an idempotency-key header in the backend contract — out of scope for v2-P0.
- Keep watch's consecutive-failure cap but make its exit deterministic and documented (compose with §3 timeout semantics: whichever bound trips first, with a distinct exit).

---

## 6. Machine-readable output requirements

### Evidence (source / live)
- JSON-on-stdout + `{"error":{status,code,message}}` envelope on stderr + exit codes are the strongest part of v1 (audit §3) — **keep the contract unchanged**.
- Heavy payloads: `dashboard --output json` returns one large nested object (summary, hierarchy, running_jobs, active_executions, activity, runtime, capability). Focused endpoints (activity, run, report, leaderboard) are lean.
- Schema drift: `leaderboard model --history` names the field `benchmark_version`; `run list`/`report list` use `benchmark_version_id`; `activity --type` returns three structurally different item shapes (benchmarks `{name,state,id}`, executions `{id,benchmark_name,target_model,status,…}`, models `{name,last_executed_at,execution_count}`).
- No `--fields`/projection and no JSON-schema self-description exist today.

### Recommended contract (no "agent mode")
- **`--fields` projection**, applied uniformly across `--output json`: dot-path selectors (`--fields id,status,completed_items`) returning a pruned object while the identifiers stay fully stable for back-compat. Default output unchanged.
- **Schema self-description** (cheap, extremely agent-friendly): `atlas schema <command...>` or `--output json-schema` emitting the pydantic model JSON schema per response type, so agents can introspect shapes instead of learning them empirically (fixes P9/P10 drift without renaming fields and breaking anything).
- **Naming consistency for new fields only**: adopt one convention (`*_id` for all FK uuids) going forward; do not rename existing fields in v2 (back-compat), but document aliases if a backend contract change touches serializers anyway (§1 Option A may give a natural point to also normalize `benchmark_version` → `benchmark_version_id` with the engine change).

---

## 7. Backend-vs-CLI ownership summary (who commits what, locally)

| Work item | Owner | Prerequisite |
|---|---|---|
| §1 Unify execution authority (`GET /executions/{id}` reads authoritative row; keep engine internals internal) | **Backend** (routers + repository + tests) | none (this is the top P0) |
| §1 Fix `started_at`/`completed_at` on authoritative surface | **Backend** | §1 |
| §2 Public catalog read rule (get/versions published exemption) + real submit authz | **Backend** (authz + routes + tests) | none |
| §3 `watch --timeout` + exit-code addition + last-state-on-timeout JSON | **CLI/SDK** (+ contract note in exit-code docs) | §1 (watch should poll authoritative state) |
| §4 submit default + `--preview` (requires read-only preview endpoint if absent) | **CLI** for defaults; **Backend** for preview endpoint | backend preview endpoint if chosen |
| §5 `--retries` global (map to SDK) | **CLI** | none |
| §6 `--fields` + `--json-schema` | **CLI/SDK** | none |

Nothing above is implemented in this commit — this document is the design input. The v2 implementation plan (slices, tests-first, local commits) will be drafted from this document next, pending your approval.

## 8. Verification notes from this investigation

- Live reproduction of §1 drift: run `bf6c70b3-0f23-451d-9c1d-1e84f41bb63d` (RUNNING via `run get`; COMPLETED via `report list/get`, `report export`, dashboard). Source-grounded cause identified above.
- Live reproduction of §2: `atlas benchmark get/versions <published-id>` → exit 4; `atlas run submit <version-id>` → exit 0.
- Retry claim verified at `sdk/python/atlas_sdk/client.py:55-63,148-214,272-282`.
- Watch loop verified at `cli/cli/commands/run.py:272-354` (no wall-clock bound).
- Nothing was changed; only this document added.