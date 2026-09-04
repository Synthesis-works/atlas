# Atlas CLI v3 — Agentic Layer (Gemini-CLI-style) Investigation & Design

> **Status:** Design/decision input only. **No code changed.**
> **Branch under consideration:** `feature/atlas-cli-v3` (to be created from `feature/atlas-cli-v2` at `84b1a4f`).
> **Goal shape:** `atlas` → interactive REPL agent loop; `atlas "task..."` → non-interactive one-shot; `atlas <cmd> ...` → unchanged deterministic CLI mode.

## 0. Executive summary

This document investigates how to turn the Atlas CLI into a Gemini-CLI-style
**agentic terminal** while preserving the deterministic commands as the
execution layer underneath. Key conclusions:

- The existing v1/v2 CLI is a clean, regular, deterministic foundation: every
  command is `click → build_client(cfg) → AtlasClient SDK method → typed DTO →
  renderer`, with a shared `error_exit` → exit-code mapping. The agent layer
  should sit **on top** of this, never replacing it.
- A full **backend** agent loop already exists (`apps/backend/agent/`:
  `AtlasAgent`, `ToolRegistry`, `ProviderRouter`, `GeminiAgentProvider`), but it
  is **server-side and authoring-oriented** (create dataset → run benchmark →
  generate report). The CLI agent needed here is **client-side and
  control-plane-oriented** (query readers + submit/watch/report on the caller's
  own runs). We reuse its **patterns** (Gemini function-declaration tool
  schemas, `AgentDecision`-style structured model), not its server loop.
- **Decision (user-approved):** the agent's LLM "brain" = **reuse
  `packages/llm` `GeminiClient`** (already used by the backend agent, hand-rolled
  httpx REST client with native Gemini function calling, no new `uv` dependency).
- **Decision (user-approved):** the loop runs **client-side in the CLI**. The
  agent's tools call the **same `AtlasClient` SDK methods** the deterministic
  commands already use, so tools and CLI can never drift.
- **Decision (user-approved):** the existing **Gemini model-name inconsistency**
  (four divergent values across the repo) is **deferred — documented only** for
  now; the agent's default model stays configurable.

## 1. The goal (from the user)

Turn Atlas CLI into a Gemini-CLI-like agentic terminal for the Atlas platform:

```
                    atlas
                      │
              ┌───────┴────────┐
              │                │
        Normal commands     Agent mode
              │                │
     atlas run ...       atlas "task"
     atlas benchmark...       │
     atlas report ...         ▼
     atlas model ...     Atlas Agent
                              │
                    ┌─────────┴─────────┐
                    │ Atlas tool layer  │
                    ├───────────────────┤
                    │ benchmarks models  │
                    │ runs reports       │
                    │ leaderboards       │
                    │ execution/watch    │
                    │ export             │
                    └─────────┬─────────┘
                              │
                              ▼
                       Atlas SDK / API
```

Two personalities:
- **CLI mode**: precise, deterministic, scriptable (unchanged).
- **Agent mode**: exploratory, conversational, multi-step.

The defining property of agent mode is the **loop**:

```
USER INTENT → LLM REASONING → TOOL CALL → ATLAS → OBSERVATION →
→ LLM REASONING → MORE TOOLS if necessary → FINAL RESPONSE
```

"Like Gemini CLI" is **not** `atlas ask "..."` returning an LLM paragraph; it is
a loop that can *call tools against the Atlas platform and consume their
observations across multiple steps*.

## 2. The deterministic foundation (current v2 state, all preserved)

### 2.1 CLI structure (`cli/`)
- `cli/cli/app.py`: root `main` click group (`invoke_without_command=True`),
  global options (`--output/-o`, `--base-url`, `--profile`, `--timeout`,
  `--retries`, `--no-color`, `--quiet`, `--version`), a `Context` object
  (`ctx.config: AtlasConfig`) passed to every subcommand via `_pass_context`.
  Prints help when no subcommand is invoked (`app.py:117-118`) — this is the
  natural hook for `atlas` → interactive REPL.
- `cli/cli/config.py`: `AtlasConfig` (base_url, timeout, output, profile,
  no_color, quiet, token, retries), `load_config()` precedence (flags > env >
  saved profile > defaults), credentials persisted in
  `%APPDATA%\Atlas\config.toml`.
- `cli/cli/client.py`: shared `build_client(cfg, *, token_supplier, timeout)`
  → `AtlasClient`. All commands use it as a context manager.
- `cli/cli/errors.py` + `cli/cli/output/errors.py`: exit codes (0-9, 130),
  `error_exit(exc, output_mode)` mapping SDK exceptions → codes.
- `cli/cli/output/{json,table,schema,quiet}.py`: renderers. `render_json`
  dumps whatever it is given (no auto-envelope); JSON-mode errors go to stderr
  as `{"error":{status,code,message,details}}`.

### 2.2 Capability → Endpoint → SDK method map (the agent's tool palette)

| Capability | CLI | SDK method | Endpoint |
|---|---|---|---|
| Auth | `login`/`logout`/`whoami` | `login` / `whoami` | `/api/v1/auth/*` |
| Health | `health` | `health_summary` etc. | `/health`, `/api/v1/system/*` |
| Dashboard | `dashboard` | `get_dashboard` | `/api/v1/dashboard` |
| Activity | `activity --type` | `get_recent_benchmarks/executions/models` | `/api/v1/history/*/recent` |
| Benchmarks | `benchmark list/get/versions` | `list_benchmarks`/`get_benchmark`/`list_benchmark_versions` | `/api/v1/benchmarks*` |
| Leaderboards | `leaderboard benchmark/model` | `get_benchmark_leaderboard`/`get_model_summary|history|benchmarks` | `/api/v1/models/{name}/*`, `/benchmarks/{bv}/leaderboard` |
| Models | `model list` | `list_models` | `/api/v1/models` |
| Runs (submit/preview) | `run submit --target-model [--preview]` | `submit_execution` / `list_dispatch_targets` | `POST /benchmarks/{bv}/executions`, `GET /executions/dispatch-targets` |
| Runs (get/list) | `run get` / `run list` | `get_execution` / `list_executions` | `/api/v1/executions*` |
| Runs (watch) | `run watch --timeout` | `get_execution` (polling) | `/api/v1/executions/{id}` |
| Runs (cancel) | `run cancel` | `cancel_execution` | `POST /executions/{id}/cancel` |
| Reports | `report list/get/export` | `list_report_runs`/`get_report_run`/`export_report_run` | `/api/v1/reports/runs*` |

### 2.3 SDK layer (`sdk/python`)
- `atlas_sdk/client.py`: `AtlasClient` with `StaticTokenSupplier` auth,
  `timeout`/`max_retries`, `_unwrap` (enveloped `APIResponse.data`),
  `_parse_bare`/`_get_raw` (direct data), `_post` never retried.
- `atlas_sdk/models/*`: typed DTOs (`BenchmarkRead`, `ModelRead`,
  `ExecutionResponse`, `ReportSummaryRead`, `LeaderboardRead`, …).

### 2.4 Why the agent can reuse this wholesale
The CLI already speaks structured JSON (`--output json`) and typed DTOs. The
agent's "observations" are simply the same DTOs the deterministic commands
render. There is **no new capability** the agent needs beyond what the SDK
already provides — the only new piece is the **LLM reasoning + tool-dispatch
loop** in the CLI.

## 3. Reusable existing agent infrastructure (patterns, not the loop)

`apps/backend/agent/` already provides battle-tested patterns to mirror:

- `state.py`: `AgentTask`, `AgentDecision`/`AgentDecisionType`, `PlanStep`,
  `ToolCallRecord`, `ObservationRecord`, permission model, hard limits.
- `tools/base.py` + `tools/registry.py`: `BaseTool` with
  `get_gemini_schema()` (UPPERCASE JSON-schema types) and an abstract
  `execute()`; `ToolRegistry` builds Gemini `functionDeclarations`.
- `providers/gemini.py`: `GeminiAgentProvider` drives the loop with native
  Gemini function calling via `GeminiClient`, sending `functionDeclarations`
  in the `generateContent` payload and parsing the `functionCall` response.
- `planner.py`, `executor.py`, `memory.py`: orchestration + prompt context.

**But**: the backend loop is server-side and *authoring*-oriented (its tools
create datasets/benchmarks and run whole evaluations server-side). The CLI
agent is *client-side* and *control-plane*-oriented (read queries + submit the
caller's own run + watch + report + export). Therefore we do **not** route the
CLI agent through `POST /api/v1/agent/tasks`. Instead the CLI hosts a
**local loop** whose tools invoke the **same SDK methods** as the deterministic
commands (§2.2).

We adopt the same *shape*: a `BaseTool`-like contract, a tool registry that can
emit Gemini `functionDeclarations`, and a provider-style `decide()` that
returns a structured next-action (call tool X with args Y / clarify / finalize)
rather than free text.

## 4. Proposed architecture (client-side)

```
atlas                          → interactive REPL (agent mode)
atlas "Find the latest ..."    → non-interactive one-shot agent run
atlas benchmark list ...       → unchanged (CLI mode)
```

### 4.1 Entrypoint wiring (`cli/`)
Two minimal additions to `cli/cli/app.py`, preserving all existing commands:

1. **One-shot agent:** a new hidden-style subcommand (or a `--agent "task"`
   global flag) that runs the loop once over a quoted task string and exits
   with a documented code. Proposed surface:
   ```
   atlas "task..."            # non-interactive (best effort)
   ```
   Because `main` is `invoke_without_command=True`, a bare quoted string is not
   currently a valid invocation; we must decide the exact surface (see §6.1).
2. **Interactive REPL:** fill the `invoked_subcommand is None` branch
   (`app.py:117-118`) so that bare `atlas` (no args, TTY) starts the REPL
   rather than printing help. Non-TTY / piped `atlas` should keep printing help
   so existing scripts that generate help are unaffected.

### 4.2 New modules in `cli/cli/` (proposed)
- `cli/cli/agent/__init__.py`
- `cli/cli/agent/tools.py` — **tool layer**: one tool per §2.2 capability. Each
  tool wraps `build_client(cfg)` → SDK method → typed DTO. Exposes a Gemini
  `functionDeclarations` schema + an `execute(args) -> observation` contract
  (JSON-serializable). This is the "Atlas tool layer" in the user's diagram.
- `cli/cli/agent/loop.py` — the **loop**: LLM `decide` → dispatch tool →
  observation → repeat until final answer; enforces step/tool-call/deadline
  limits.
- `cli/cli/agent/provider.py` — thin adapter over `packages/llm`'s
  `GeminiClient` that mirrors `backend .../providers/gemini.py`'s
  `decide(...) -> Decision` contract, but client-side.
- `cli/cli/agent/repl.py` — interactive REPL: `You >` / `Atlas >` rendering,
  tool-call progress (`✓ benchmark list`, `✓ model list`, …), Ctrl-C handling.
- `cli/cli/agent/state.py` — small local state Pydantic models
  (`AgentTask`, `ToolCallRecord`, `ObservationRecord`, `AgentDecision`,
  limits), mirroring the backend `state.py` shape but scoped to CLI needs.
- `cli/cli/agent/prompt.py` — builds the system + dynamic context for the LLM
  from the user task + tool results, Gemini-CLI-tone.

### 4.3 Dependency (user-approved: reuse `packages/llm`)
- `cli/` gains a dependency on **`packages/llm`** (the shared client library),
  or vendors the minimal `GeminiClient` directly. Preferred: declare
  `packages/llm` as a path/local dependency of `cli` in `cli/pyproject.toml`
  and add it to the workspace/`uv` dependency graph (AGENTS.md §4: modify
  `pyproject.toml` + regenerate `uv.lock` via `uv`). No third-party LLM SDK is
  introduced.
- **Phase 1a wiring (implemented):** `uv path-deps` are not viable in this env
  (`uv run` requires building `atlas-sdk` → `pyyaml` against MSVC C++ Build
  Tools, which are absent). Instead `packages/llm` is wired into the CLI by:
  1. adding `D:/atlas/packages` to global `sys.path` via
     `site-packages/atlas_packages.pth` (mirrors the pre-existing
     `atlas_db.pth` pattern), and
  2. making `packages` a regular package with a new `packages/__init__.py`, and
  3. a scoped `sys.path` bootstrap in `cli/agent/provider.py` +
     `cli/tests/conftest.py` that adds the repo root (parent of `packages`)
     only where needed — never on the global site path, so the installed
     `atlas` executable and its editable `cli` package are unaffected.
- `GeminiClient(model=..., api_key_env=...)` reads `GEMINI_API_KEY` from the
  environment (same as the backend), so the CLI agent's "brain" needs a
  `GEMINI_API_KEY` in the backend process env, independent of `atlas login`
  (which authorizes the CLI → Atlas API, not Atlas → Gemini).
- **Phase 3 note (implemented):** the loop (`cli/agent/loop.py`) mirrors the
  backend pattern of rendering the whole conversation into a per-turn
  `prompt_context` (via the new `cli/agent/prompt.py`'s `build_context`), so
  observations are sent back to Gemini as a rendered transcript rather than via
  a multi-turn-native provider API — the Phase 1 `AgentProvider` is unchanged.
  Every tool call / observation is recorded in `AgentContext`; unknown-tool,
  malformed-argument, and tool-exception failures become failing observations
  (never escaping tracebacks); and steps / tool-call ceiling / wall-clock
  deadline are enforced with the authoritative `GoalExceededError`. The loop
  accepts an injectable `confirm` hook (added in Phase 4) that gates WRITE
  tools; `None` auto-approves.
- **Phase 4 note (implemented):** the CLI surface wraps the Phase 3 loop:
  `cli/agent/repl.py` provides the interactive `AgentREPL` (`You >` / `Atlas >`,
  per-turn session history, Ctrl-C/EOF clean exit, `[ok]`/`[!]` tool-progress
  with an ASCII fallback for non-UTF-8 consoles) and the non-interactive
  `run_one_shot` (auto-approve, no prompts). `app.py` wires a new `atlas agent
  "task"` subcommand and routes a bare interactive `atlas` (stdin TTY) into the
  REPL — non-TTY/piped `atlas` still prints help so automation is unaffected.
  WRITE tools are gated by the loop's `confirm` hook (prompted in the REPL,
  auto-approved in one-shot); a rejected mutation is recorded as a structured
  *declined* observation (not an execution failure). Brain-unavailable
  (`GEMINI_API_KEY` unset) refuses to start with **exit code 10**
  (`AGENT_UNAVAILABLE`), and only that case maps to 10 — unrelated agent/SDK
  errors map through the usual codes.
- **v3.1 note (implemented):** the agent brain is no longer single-provider.
  `cli/agent/provider.py` was refactored into an `LLMProvider` abstraction
  (`GeminiProvider`, `GroqProvider`) plus an availability classifier, and
  `cli/agent/router.py` adds a `ProviderRouter` that presents the same
  `decide()` surface to the loop while (by default) trying **Groq → Gemini**
  in order. Fallback happens **only** for genuine availability failures (no key,
  DNS/network, timeout, 429, 5xx); invalid-key, invalid-request, and malformed
  output return a `FAIL` decision instead of bouncing providers. `atlas agent`
  gains a `--provider auto|groq|gemini` flag (`auto` = fallback router, default);
  `--provider groq|gemini` pins and disables fallback. The loop, tool registry,
  and all 14 tools are unchanged. Docs: §5.2, §5.6, §6.4 below.
- **v3.2 note (benchmark authoring, implemented):** the agent tool surface now
  covers authoring, but **only through the existing backend `/api/v1` write
  routes** — the agent never fabricates HTTP. Eight tools were added in a new
  `cli/agent/tools/authoring.py`: two READ discovery tools
  (`list_organizations`, `list_projects` — the minimal reads a `create_benchmark`
  needs to find a `project_id`) and six WRITE tools (`create_benchmark`,
  `update_benchmark`, `create_benchmark_version`, `publish_benchmark_version`,
  `archive_benchmark_version`, `delete_benchmark`). The SDK (`AtlasClient`)
  gained the matching writers (`create/update/delete_benchmark`,
  `create/publish/archive_benchmark_version`, `list_organizations`,
  `list_projects`) plus `_put`/`_delete_raw` helpers. Confirmation model (user-
  confirmed): **all** WRITE tools prompt in the REPL (one-shot still
  auto-approves); destructive operations (`delete_benchmark`,
  `archive_benchmark_version`) set `BaseTool.destructive=True` for a **stronger
  double-confirm** prompt. Live backend semantics surfaced as typed SDK errors
  (e.g. publish/delete rejected on a benchmark whose state machine forbids it)
   are reported back to the agent as failed observations for it to relay. Docs:
   §5.4, §5.5 below.
- **v3.3 note (dataset capability parity, implemented):** the agent can now do
  everything for datasets that the web agent can — but **over the legitimate
  `/api/v1` REST surface via the SDK**, never by replicating the web agent's
  direct-DB writes (`apps/backend/agent/tools/dataset_tools.py` bypasses
  authz). This required three **new legitimate backend endpoints** so both the
  CLI agent and the web agent can converge on one clean API/SDK chain:
  `PUT /projects/{project_id}/datasets/{dataset_id}` (metadata update),
  `POST …/datasets/{dataset_id}/tasks` (append a new version with tasks), and
  `POST …/datasets/{dataset_id}/validate` (lifecycle check). Six CLI tools land
  in `cli/agent/tools/datasets.py`: `list_datasets`, `get_dataset` (READ) and
  `create_dataset`, `update_dataset`, `upload_dataset_tasks`, `validate_dataset`
  (WRITE, single-confirm; none destructive). The SDK gained matching methods and
  DTOs. The backend `DatasetService` was rewritten to own version/task seeding
  (create-with-tasks, upload-new-version, validate, enriched get). Docs: §5.4,
   §5.5 below.
- **v3.4 note (evaluation capability parity, implemented):** the agent can now
  read evaluation outcomes, author evaluation-case metadata, compare executions,
  and persist reports — **over the legitimate `/api/v1` REST surface via the
  SDK**, never by replicating the web agent's direct-DB writes
  (`apps/backend/agent/tools/evaluation_tools.py` bypasses authz) nor the legacy
  synchronous `EvaluationService.evaluate_execution()` shortcut. This required
  **five new legitimate backend endpoints**: `GET …/executions/{eid}/evaluation-results`
  (read results of a completed evaluation), `POST …/datasets/{did}/evaluation-cases`
  (merge eval-case metadata into test-case expected_output), `POST …/executions/compare`
  (read-only best-first ranking), `POST …/reports` (create/persist a report) and
  `GET …/reports` (list). A new `EvaluationParityService` backs them. Six CLI
  tools land in `cli/agent/tools/evaluation.py`: `get_evaluation_results`,
  `compare_results`, `list_report_runs` (READ) and `evaluate_run`
  (enqueues the async Celery evaluation), `create_evaluation_cases`,
  `generate_report` (WRITE, single-confirm; none destructive). The SDK gained
  matching methods/DTOs. Crucially `evaluate_run` triggers the **legitimate
  async enqueue flow** (`POST …/executions/{eid}/evaluate` → Celery → 202) and
  the agent then polls `get_evaluation_results`; evaluation is never run
  synchronously on the API thread. Docs: §5.5 below.

### 4.4 Auth model
- **CLI ⇄ Atlas API:** use the existing `AtlasConfig` token via
  `build_client(cfg)` (from `atlas login`).
- **CLI ⇄ Gemini (brain):** `GEMINI_API_KEY` env (or a configurable
  `api_key_env` / `--agent-model`), separate from Atlas auth. Default model
  configurable via `AGENT_MODEL` env / `AtlasConfig.agent_model` field (the
  concrete default is deferred — see §5.3). When the brain is unavailable, the
  agent refuses to start with exit 10 (§6.4).

## 5. Design decisions & open questions

### 5.1 Loop location — client-side ✅ (user-approved)
Rejected: routing through backend `POST /api/v1/agent/tasks`. Rationale: the
backend loop authoring-oriented and would not exercise the CLI's deterministic
commands; a client loop using the same SDK means the agent *is* the CLI.

### 5.2 LLM brain — reuse `packages/llm` ✅ (user-approved)
Rejected: adding `google-genai` via `uv` (full streaming parity but heavier
dependency + couples CLI to backend provider stack). Accepted trade-off:
`GeminiClient` has **no streaming** (`supports_streaming()==False`). The REPL
should reflect that (show progress via tool calls, not token-by-token output).

### 5.3 Gemini model-name inconsistency — defer, document only ✅ (user-approved)
Four divergent values exist:
- `config/providers.json` → `gemini-2.5-flash`
- `packages/llm/clients/gemini.py:list_models()` → `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`
- `apps/backend/config.py:110` default → `gemini-3.5-flash-lite`
- backend agent `state.py:155` default → `gemini-3.5-flash-lite`
- CLI/SDK `run submit` default target model → `gemini-2.5-flash`

This is a genuine **doc/code conflict** flagged per AGENTS.md §9. For the agent
work we **do not** standardize the repo defaults (out of scope, risky); we make
the agent's model **configurable** (`--agent-model` / `AGENT_MODEL` / config
field, defaulting deliberately and documented). A separate follow-up should
reconcile the backend/execution defaults.

### 5.4 Tool permission / safety
Deterministic CLI mode is unchanged (it already enforces auth + exit codes).
Agent mode tools run **as the logged-in user** with **no elevated
permissions** — the same backend auth the equivalent `atlas` command would
have (e.g. `run submit` still requires a dispatchable target; `report export`
still requires the caller to own/see the run). For interactive `--preview`
confirmation before any mutating POST (`run submit`), propose a **confirmation
gate** in the REPL for writes (submission/export), mirroring the backend agent's
permission model, before committing.

> **v3.2 confirmation model (implemented):** every WRITE authoring tool prompts
> in the REPL via the same `confirm` hook used by `run submit`. Destructive
> authoring tools (`delete_benchmark`, `archive_benchmark_version`) additionally
> flag `BaseTool.destructive = True`, and the REPL's default
> `_prompt_confirm` issues a second, explicit "Really …? This cannot be undone."
> prompt for those. One-shot mode (`confirm=None`) auto-approves all writes,
> unchanged from v3.1.

### 5.5 Tool set (initial)
Start with **read + submit + watch + report + export** — the exact trace from
the v2 acceptance audit:
- `model list` (choose a target)
- `benchmark list` / `benchmark get` / `benchmark versions`
- `run list` / `run get` / `run submit --preview` / `run submit` / `run watch` / `run cancel`
- `report get` / `report list` / `report export`
- `leaderboard model --history` (summarize performance)

> Tool schema note: `--output json` already gives the agent machine-readable
> observations, so each tool returns the **DTO (json-able)**, not rendered text.
> This keeps observations structured for LLM reasoning.
>
> **v3.2 authoring tools (added):** `list_organizations` (READ),
> `list_projects` (READ), `create_benchmark` (WRITE), `update_benchmark`
> (WRITE), `create_benchmark_version` (WRITE), `publish_benchmark_version`
> (WRITE), `archive_benchmark_version` (WRITE+destructive),
> `delete_benchmark` (WRITE+destructive) — bringing the registered tool count
> from 14 to 22.
>
> **v3.3 dataset tools (added):** `list_datasets` (READ), `get_dataset`
> (READ), `create_dataset` (WRITE), `update_dataset` (WRITE, no-op guard),
> `upload_dataset_tasks` (WRITE), `validate_dataset` (WRITE) — all via the
> legitimate REST/SDK chain (three new backend endpoints back these), bringing
> the registered tool count from **22 to 28**. None are destructive. See §4.3.
>
> **v3.4 evaluation tools (added):** `get_evaluation_results` (READ),
> `compare_results` (READ, non-mutating compare), `list_report_runs` (READ),
> `evaluate_run` (WRITE — enqueues the async Celery evaluation), 
> `create_evaluation_cases` (WRITE), `generate_report` (WRITE) — all via the
> legitimate REST/SDK chain (five new backend endpoints back these), bringing
> the registered tool count from **28 to 34**. None are destructive. See §4.3.

### 5.6 Exit codes in agent (one-shot) mode
Reuse the existing `ExitCode` table where a single tool failure is the cause
(e.g. `run submit` forbidden → exit 4). Add only what's needed for the loop
itself — one new code: **exit 10 = `AGENT_UNAVAILABLE`** (no Atlas agent brain
configured — no `GROQ_API_KEY`/`GEMINI_API_KEY` — or every provider offline; see
§6.4), leaving exit 9 (watch timeout) and 130 (interrupt) intact.

## 6. Final decisions (user-confirmed)

1. **One-shot surface:** `atlas agent "task text"` — an explicit `agent`
   subcommand for non-interactive runs; **bare `atlas`** = interactive REPL
   (fills the `invoked_subcommand is None` branch). This reserves the `agent`
   name, is unambiguous, and keeps the interactive + one-shot entrypoints
   distinct.
2. **Milestone 1 scope:** ship **REPL + one-shot together** in the first slice.
3. **Write confirmation:** the interactive REPL **prompts before mutating
   actions** (`run submit`, `report export --force` overwrite); one-shot
   `atlas agent "..."` **auto-confirms** (stays non-interactive). This mirrors
   the backend agent's permission gate.
4. **Brain unavailable:** the agent **refuses to start** with a clear message
   and a **new exit code 10** when no LLM brain is configured
   (`GROQ_API_KEY`/`GEMINI_API_KEY` both unset) or every configured provider is
   offline. Exit 10 (`AGENT_UNAVAILABLE`) is unused by every existing condition.
   An explicit `--provider groq|gemini` that is unavailable also exits 10.

## 6.1 Remaining open questions

_None — all outstanding items resolved above._

Additionally, future reconciliation of the Gemini model-name inconsistency
(§5.3) should be its own follow-up, not folded into this slice.

## 7. Recommended phasing (after sign-off)

- **Phase 0 (design gate, done):** this document.
- **Phase 1:** add `packages/llm` dependency to `cli` (uv/pyproject/lock);
  scaffold `cli/cli/agent/` skeletons + shared state/limits (tests-first).
- **Phase 2:** client-side tool layer (one tool per §2.2 capability) backed by
  the SDK; tests against mocked `AtlasClient`.
- **Phase 3:** the loop (`decide` → dispatch → observe) over `packages/llm`
  `GeminiClient`; structured `AgentDecision`; limits.
- **Phase 4:** interactive REPL (`You >` / `Atlas >`, progress `✓ ...`,
  Ctrl-C) + one-shot mode (§6.1) + wiring in `app.py`.
- **Phase 5:** docs (architecture, manual-testing, IMPLEMENTATION_HISTORY,
  v3 plan) + live verification against the running backend + gemini key.
- Cross-cutting: tests-first, ruff/mypy clean, commit locally only on
  `feature/atlas-cli-v3` (per AGENTS.md §9 and the established v2 practice).

## 8. Non-goals / guardrails
- Keep the deterministic CLI byte-for-byte compatible (no changes to existing
  command behavior, exit codes, or JSON shapes).
- No new repo-wide backend changes; the agent is a **CLI-layer** feature.
- Do not wire the CLI agent into the backend `/agent/tasks` server loop.
- No `google-genai`/`openai`/`anthropic` SDK dependencies by default.
- Do not standardize the Gemini model-name conflict in this change (deferred).
