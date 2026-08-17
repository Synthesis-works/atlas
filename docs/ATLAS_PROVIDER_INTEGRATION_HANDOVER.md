# Atlas Agent Provider Integration — Handover

**Date:** 2026-08-15
**Status:** Complete. Ready for manual real-provider E2E verification.
**Do NOT commit anything.** All work remains uncommitted in the worktree below.

> This is the **authoritative handover** for the Atlas Agent multi-provider integration.
> It was produced by Big Pickle (opencode) at the end of a takeover session that
> continued uncommitted work started in an Antigravity session.
> **Next agent MUST read this document first**, then `docs/AGENT_HANDOFF.md`.

---

## A. Current worktree path and git branch

- **Worktree:** `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\implement_atlas_agent_loop`
- **Branch:** `implement_atlas_agent_loop`
- **HEAD:** `f9d8177` (unchanged — nothing committed during the takeover)
- **Do NOT work in `D:\atlas`** — it has no `apps/backend/agent`. All agent code lives in this worktree.
- **Python:** worktree venv `.venv\Scripts\python.exe` (Python 3.14.3, `uv`-managed).
  Use `.venv\Scripts\python.exe -m pytest ...` (or activate `.venv`).

---

## B. Exact files created / modified by this takeover

### Created by this takeover
- `apps/backend/agent/tests/test_provider_contracts.py` — new 20-test contract suite (all mocked).
- `apps/backend/agent/providers/schema_utils.py` — recursive schema normalizer + `extract_json_object()`.
- `ATLAS_PROVIDER_INTEGRATION_WALKTHROUGH.md` (repo root) — detailed working record; this handover supersedes it for next-agent navigation.
- `docs/ATLAS_PROVIDER_INTEGRATION_HANDOVER.md` — this file.

### Modified by this takeover (critical fixes)
- `packages/llm/clients/groq.py` — tools passthrough into payload; `content=None` robustness.
- `apps/backend/agent/providers/groq.py` — JSON text-fallback via `extract_json_object()`; mypy fixes.
- `apps/backend/agent/providers/mistral.py` — same JSON fallback fix; mypy fixes.
- `apps/backend/agent/providers/router.py` — primary-exclusion in auto fallback chain; `_provider_value()`.
- `apps/backend/routers/agent.py` — `AgentTask.model=None` validation fix; `/providers` metadata fields; removed unused import; mypy annotation.
- `tests/test_agent_api.py` — added 3 `/providers` endpoint tests (now 13 tests total).

### Pre-existing (from the earlier Antigravity session, verified, NOT touched)
- `apps/backend/agent/providers/router.py` (registry refactor — see §D)
- `apps/backend/agent/providers/groq.py` (initial version), `grok.py`, `mistral.py` (normalization wiring)
- `apps/backend/agent/providers/mock.py` (test-only provider)
- `apps/backend/routers/agent.py` (provider param, `_run_agent_task_background`, `/providers` route)
- `apps/backend/main.py` (agent router at `/api/v1`, `/agent-ui` static mount)
- Frontend: `apps/landing/src/pages/workspace/agent/` (`AgentDashboard.tsx`, `AgentSidebar.tsx`, `AgentTimeline.tsx`, `AgentWorkspaceRun.tsx`, `AgentLayout.tsx`) and `apps/landing/src/features/agent/` (services, types, polling). Dashboard dynamically consumes `GET /api/v1/agent/providers` and filters `!p.is_test_only`.

---

## C. Every bug discovered and fixed

1. **Groq client never sent `tools` (the #1 blocker).**
   `GroqClient.generate()` built the chat-completions payload without forwarding `tools`, so Groq tool calling was impossible. Fix: `if "tools" in kwargs and kwargs["tools"]: payload["tools"] = kwargs["tools"]` in `packages/llm/clients/groq.py` (mirrors Mistral/Grok clients).

2. **Groq client crashed on `content=None` tool-call responses.**
   `data["choices"][0]["message"]["content"]` was None for pure `tool_calls` messages; `LLMResponse.response` (required `str`) raised a pydantic `string_type` error before `raw.tool_calls` could be read — breaking native tool calling. Fix: `.get("content") or ""`.

3. **Every API task creation failed pydantic validation (`string_type`).**
   `TaskCreateRequest.model` is `Optional[str] = None`, but `AgentTask.model` is a required `str`. Passing `payload.model=None` explicitly raised a validation error. Fix in `apps/backend/routers/agent.py`: only assign `model` when provided, letting `AgentTask` keep its default (`gemini-3.5-flash-lite`).

4. **`ProviderRouter(primary=X)` duplicated the primary in its fallback chain.**
   `ProviderRouter(primary=gemini)` produced `[gemini, gemini, groq, mistral]`, wasting a full extra attempt on the same provider. Fix: `_provider_value()` and exclude the primary's registry value when building fallbacks.

5. **JSON text-fallback truncated nested tool arguments.**
   The regex `re.search(r"(\{.*?\})")` stopped at the first `}` of a nested object, producing invalid JSON and silently returning a text response instead of a tool call. Fix: shared balanced-brace `extract_json_object()` in `schema_utils.py`, used by both Groq and Mistral providers.

6. **Schema normalizer was shallow (mypy/requirement gaps).**
   Only `properties`/`items` were normalized; `additionalProperties`, `not`, `anyOf`/`oneOf`/`allOf`/`prefixItems`, `patternProperties` were not; `type` values like `NUMBER`/`INTEGER` were not always lowercased; and the input dict was mutated in place (corrupting the canonical Gemini schema). Fix: explicit `_TYPE_MAP`, full recursion, preservation of `required`/`enum`, and a no-mutation guarantee (new tree per call, verified by test).

7. **Mypy errors in delivered provider files.**
   `self.model` untyped (`str`), and `response.raw` Optional access (`(response.raw or {})`). Fixed in `groq.py`/`mistral.py`.

---

## D. Provider architecture as it exists NOW

- **Single source of truth:** `PROVIDER_REGISTRY` in `apps/backend/agent/providers/router.py`
  (`ProviderConfig`: value, label, description, model, `is_test_only`, `api_key_env`).
- **`get_configured_providers()`** filters registry by API-key presence in env (and test-only).
- **`build_provider_instance(value, model_override=None)`** instantiates a provider from registry value.
- **`ProviderRouter(primary=...)`** builds `[primary] + fallbacks` (primary excluded from fallbacks), classifies errors (`AUTH` / `FALLBACK` / `RETRYABLE` / `FATAL`), retries with backoff, enforces per-provider cooldowns, and appends `provider_fallback` / `provider_decision_<name>` events to `task.execution_trace`.
- **`AtlasAgent.run_task(task, db)`** drives the loop: tool schemas come from `ToolRegistry` (Gemini-style UPPERCASE); Gemini receives them natively; Groq/Mistral receive `normalize_tools_for_openai(...)` output.
- **`apps/backend/agent/providers/base.py`** defines `BaseLLMProvider` (the `decide()` interface).
- API flow: `POST /api/v1/agent/tasks {goal, provider, model?, permissions}` → `create_agent_task` stores `AgentTask` in `_agent_tasks_db` → `_run_agent_task_background` builds the requested primary via `build_provider_instance` and hands it to `ProviderRouter` → `AtlasAgent.run_task` → executor → tools → EventBus/Celery.

## E. Provider fallback order and routing behavior

- **Production chain:** **Gemini → Groq → Mistral** (registry order in `PROVIDER_REGISTRY`).
- `decide()` walks `[primary] + fallbacks`:
  1. Skip providers in cooldown or with unhealthy/missing keys.
  2. On `FAIL`, classify: **AUTH** (401/403/bad key) → fallback + 120s cooldown; **FALLBACK** (400/404/model missing/no credits) → fallback + 120s cooldown; **RETRYABLE** (429/5xx/timeout) → up to `max_retries_per_provider` retries with backoff, then fallback + 60s cooldown; **FATAL** (schema/state corruption) → fail immediately.
  3. Record each fallback and successful decision in `task.execution_trace`.
  4. If all fail, return `FAIL` with `"All LLM providers in fallback chain failed: gemini: ...; groq: ...; mistral: ..."` — preserving per-provider info.

## F. Provider status and limitations

| Provider | Status | Notes |
|---|---|---|
| **Gemini** | Primary, default | `gemini-3.5-flash-lite`. Native `functionDeclarations`, schema sent unchanged. Quota is precious — do NOT run real-API tests casually. |
| **Groq** | Fallback 1 | `llama-3.3-70b-versatile`. OpenAI-compatible tool calling (fixed), `extract_json_object` text fallback. |
| **Mistral** | Fallback 2 | `mistral-small-latest`. Same normalization/fallback handling as Groq. |
| **Grok (xAI)** | Excluded | Code preserved in `grok.py`; registry entry commented out — no credits, deprecated model IDs. Re-enable by un-commenting its `ProviderConfig` once funded. |
| **Mock** | Test-only | `is_test_only=True`, filtered out of `/providers` and hidden from UI. |

## G. Schema normalization implementation and why it exists

Atlas tool schemas originate in `tools/base.py` in Gemini `functionDeclaration` format with **UPPERCASE** types (e.g. `{"type": "OBJECT", "properties": {"count": {"type": "INTEGER"}, "tags": {"type": "ARRAY", "items": {"type": "STRING"}}}}`). OpenAI-compatible providers (Groq/Mistral) require lowercase JSON Schema types.

`normalize_tools_for_openai()` in `apps/backend/agent/providers/schema_utils.py`:
- Lowercases `type` via explicit `_TYPE_MAP` (OBJECT→object, STRING→string, INTEGER→integer, NUMBER→number, BOOLEAN→boolean, ARRAY→array, NULL→null), passing through already-lowercase.
- Recurses into `properties`, `items`, `additionalProperties`, `not`, `anyOf`/`oneOf`/`allOf`/`prefixItems`, `patternProperties`.
- Preserves `required` and `enum` as plain lists.
- **Never mutates the input** — produces a brand-new dict tree, so Gemini's canonical schema stays untouched (verified by test).

## H. JSON extraction implementation and why it exists

When a provider returns tool arguments as text (rather than a structured `tool_calls`), the fallback must extract the JSON. The old `re.search(r"(\{.*?\})")` truncated at the first `}` of nested objects. `extract_json_object()` in `schema_utils.py` scans with balanced-brace counting to capture the complete outermost object, handling nested braces/arrays/strings. Used by both Groq and Mistral providers.

## I. `/providers` endpoint behavior and response semantics

- Route: `GET /api/v1/agent/providers` (router mounted at `/api/v1/agent`).
- **Derived from `PROVIDER_REGISTRY`** filtered by configured keys — no hardcoded frontend list, no live API health calls (cheap).
- Each entry returns: value, label, description, model, `is_test_only`, and now **`configured`**, **`enabled`**, **`status`** (static metadata — no live calls).
- Guarantees (tested): **never** exposes `mock`; **never** exposes `grok`; returns only configured providers.
- Frontend (`AgentDashboard.tsx`) consumes this and filters `!p.is_test_only` → dropdown lists Gemini, Groq, Mistral.

## J. Tests added and exact results

### New: `apps/backend/agent/tests/test_provider_contracts.py` (20 tests, all external calls mocked — zero Gemini quota)
- Gemini decision contract: native tool call, final response, JSON-text fallback.
- Groq/Mistral decision contracts incl. text-fallback → tool call.
- Gemini schema passed **unchanged** (no mutation).
- Recursive lowercase normalization: nested objects, `items`, `additionalProperties`, `anyOf`, `oneOf`, `NUMBER→number`.
- No-mutation guarantee of the input schema.
- Registry excludes Grok and Mock.
- Router ordering Gemini→Groq→Mistral; primary-override excludes duplicate.
- Failover: Gemini-fail→Groq; Gemini+Groq-fail→Mistral; all-fail preserves chain info.

### Added to `tests/test_agent_api.py` (3 tests; file now 13 total)
- `/providers` never exposes `mock`; never exposes `grok`; returns only configured providers with expected fields.

### Exact results (run with worktree `.venv`, Python 3.14.3)
| Command | Result |
|---|---|
| `pytest apps/backend/agent/tests/test_provider_contracts.py` | **20 passed** |
| `pytest tests/test_agent_api.py` | **13 passed** |
| `pytest apps/backend/agent/tests/test_agent_core.py apps/backend/agent/tests/test_provider_failover.py apps/backend/agent/tests/test_provider_contracts.py` | **37 passed, 2 failed** (see §L) |
| `ruff check` (all changed files) | **All checks passed** |
| `mypy` (groq.py, mistral.py, schema_utils.py, router.py, routers/agent.py, packages/llm/clients/groq.py) | **clean** (remaining repo errors are pre-existing in untouched files) |
| `npm run build` in `apps/landing` (tsc -b + vite build) | **built successfully** |
| `pytest` (full repo) | 132 passed, 22 failed, 1 skipped (see §L) |

## K. Commands used for validation

```
.venv\Scripts\python.exe -m pytest apps/backend/agent/tests/test_provider_contracts.py
.venv\Scripts\python.exe -m pytest tests/test_agent_api.py
.venv\Scripts\python.exe -m pytest apps/backend/agent/tests/test_agent_core.py apps/backend/agent/tests/test_provider_failover.py apps/backend/agent/tests/test_provider_contracts.py
.venv\Scripts\python.exe -m ruff check <changed-files...>
.venv\Scripts\python.exe -m mypy <changed-files...>
cd apps\landing && npm run build      # tsc -b && vite build
```

## L. Known failing / pre-existing tests (unrelated to this work)

1. **Concurrent "Run Again" tool contract drift** (same worktree, separate workstream — do not attribute to provider work):
   - `RunBenchmarkTool.execute()` now requires `dataset_version_id`; older callers pass only `{benchmark_version_id, target_models}` → fails `test_provider_failover.py::test_scenario_j_k_full_workflow_and_lineage_isolation`, `::test_regression_prose_decision_rejection_and_repair`, `tests/test_run_again.py::test_agent_run_again_flow`, `tests/integration/test_live_e2e_execution.py`, `tests/integration/test_e2e_execution_and_evaluation.py`.
   - `ExecutionService.create_execution()` gained `submitted_by` → `tests/execution/test_domain.py` (12 tests) + `tests/execution/test_persistence.py` fail with `TypeError`.
   - `apps/backend/agent/tests/test_evaluation_cases.py` fails at collection: `cannot import name '_benchmark_execution_store'` from `execution_tools.py`.
2. **Full-suite DB environment pollution:** API tests in `tests/` fail when the whole directory runs because `tests/execution/*` import the SQLAlchemy engine before `tests/test_agent_api.py` runs `dotenv.load_dotenv()`, leaving the engine on the PostgreSQL default (connection refused). Same tests **pass in isolation**. Test-infra fragility, not a provider defect.
3. **xAI Grok disabled** (see §F). **Gemini mypy** gaps are pre-existing in `gemini.py` (untouched).

## M. Current uncommitted changes / git status

```
M  packages/llm/clients/groq.py
M  apps/backend/agent/providers/grok.py
M  apps/backend/agent/providers/mistral.py
M  apps/backend/agent/providers/router.py
M  apps/backend/routers/agent.py
M  tests/test_agent_api.py
M  .coverage
?? apps/backend/agent/providers/groq.py
?? apps/backend/agent/providers/schema_utils.py
?? apps/backend/agent/tests/test_provider_contracts.py
?? apps/landing/src/features/agent/
?? apps/landing/src/pages/workspace/agent/
?? ATLAS_PROVIDER_INTEGRATION_WALKTHROUGH.md
?? ATLAS_AGENT_V1_QA_RESULTS.md
?? scratch/
?? tests/integration/test_agent_concurrency.py
?? t1_result.json t2.json t3.json t4.json
?? atlas_dev.db.bak
?? packages/database/alembic/versions/d13d235aadf1_add_dataset_version_isolation.py
```

Plus unrelated concurrent "Run Again" workstream changes (execution engine, alembic version deletions/rewrites, worker, dataset_tools, landing App/workspace, `apps/web/public/agent_ui.js`, seed.py) — **leave them alone**. Nothing has been committed on this branch by this takeover.

## N. Exact next steps — real-provider E2E verification (do this next)

1. Backend up: `uvicorn apps.backend.main:app --reload` from the worktree root (or the docker-compose dev flow in `docs/docker_setup.md`).
2. `curl http://127.0.0.1:8000/api/v1/agent/providers` → expect `gemini`, `groq`, `mistral` only (no `mock`, no `grok`).
3. Submit a minimal real task with Gemini primary (see §8 of `ATLAS_PROVIDER_INTEGRATION_WALKTHROUGH.md` for the exact curl).
4. Watch the chain in the landing Agent UI: Gemini reasoning → native tool call → executor → task progresses PLANNING → EXECUTING → COMPLETED.
5. Optional fallback spot-check: set `GEMINI_API_KEY` to garbage, resubmit, confirm a `provider_fallback` trace event to `groq`.
6. Only after this passes, proceed to any larger benchmark run.

## O. Risks, unfinished work, assumptions, things NOT to revert

- **Do not revert** the `3a1cf533642c` / `2256bd2b7c2c` migration rewrites (July 2026 Dockerization fix) — see AGENTS.md warning.
- **Do not commit** without explicit instruction; branch `main` must never be modified directly.
- **Assumption:** all three production API keys are present in the worktree `.env` (verified present).
- **Gemini quota is precious** — prefer mocked tests; the real E2E in §N is the only place to spend it, minimally.
- **Unfinished (pre-existing):** the "Run Again" tool contract drift (see §L) is owned by the concurrent workstream; fix there, not in provider code.
- **Migration policy:** treat committed migrations as immutable; fix forward with new migrations.

## P. Relationship to prior Atlas Agent V1.1/V1.2 work

- This provider integration rides on top of the earlier agent loop (V1.1/V1.2) that established: `AtlasAgent` loop, `ToolRegistry`, `AgentTask`/`AgentTaskStatus`/`AgentPermission` in `apps/backend/agent/state.py`, execution isolation, concurrent-run support, the React Agent UI, and the `/api/v1/agent/*` API surface.
- Execution isolation & concurrent runs: `tests/integration/test_agent_concurrency.py` (pre-existing, in working tree) exercises the loop; final executions flow through `ExecutionRunner` → `EventBus`/Celery, with dataset-version isolation (`d13d235aadf1_add_dataset_version_isolation.py`, concurrent workstream).
- The provider layer replaces the previously hardcoded single-provider behavior: `/tasks` now takes `provider` + optional `model`, routing through `ProviderRouter` with the Gemini→Groq→Mistral fallback. The React Agent UI is fully provider-driven via `/providers`.
- **Do not break** the unidirectional Execution → Evaluation dependency or the Repository Pattern when touching adjacent code.

## Q. Origin / continuation context

This work was **continued from an Antigravity session** operating in the same worktree. The pre-takeover state (registry router, provider files, UI) existed only as uncommitted working-tree files on branch `implement_atlas_agent_loop` (HEAD `f9d8177`). Big Pickle (opencode) took over in-place, fixed the critical defects, added the contract/API tests, validated, and documented. Antigravity can resume exactly where Big Pickle stopped because all state lives in this same worktree.

---

## NEXT AGENT INSTRUCTIONS

**Already completed (do not redo):**
- GroqClient tools passthrough + `content=None` fix; recursive schema normalization (no mutation); `extract_json_object` text fallback; primary-exclusion in `ProviderRouter` fallbacks; `AgentTask.model=None` API fix; `/providers` metadata.
- 20 contract tests + 3 API tests; ruff/mypy clean on changed files; frontend `npm run build` green.

**Must verify next (in order):**
1. Read `docs/AGENT_HANDOFF.md`, `docs/PROJECT_STATE.md`, `docs/IMPLEMENTATION_HISTORY.md`, `docs/docker_setup.md` (AGENTS.md required reading).
2. Re-run the validation commands in §K to confirm the baseline still passes.
3. Run the **real-provider E2E** in §N (backend up, `/providers`, one Gemini task, watch UI chain, optional Groq fallback spot-check). This is the immediate next implementation/evaluation step.

**Must NOT change:**
- Do not touch the concurrent "Run Again" workstream files (execution_engine, `execution_tools.py`/`dataset_tools.py`, worker, alembic versions, seed.py, landing App/workspace/auth).
- Do not revert migration fixes `3a1cf533642c` / `2256bd2b7c2c`.
- Do not re-enable Grok in the registry; do not expose `mock` via `/providers`.
- Do not mutate Gemini's schema in the normalizer; do not break the no-mutation guarantee.
- Do not commit anything unless explicitly asked; never modify `main`.

**Immediate next step:** Run the §N real-provider E2E with a single minimal Gemini task and confirm the fallback chain and UI progress, then report results. If §N passes, the integration is live; then optionally follow up on the pre-existing "Run Again" contract drift (owner: concurrent workstream).
