# P1 Report — Hosted Conversational Session API (v0.2.0)

Status: **implemented, gates green** on branch `wip/agent-hosted-session-api`
(mixed baseline: earlier slice committed at `8f979c9`; this report records the
completed P1 assessment including uncommitted working-tree fixes).

Scope gate: P1 = per-tool authorization security gate + session model/migration/
router + session API tests. Remaining for the full feature: P2 (not started).

## 1. Auth-scope question (answered)

> Can a JWT for user A read/modify user B / org B data through the new session
> API, and is enforcement trusted to the client?

**No, and enforcement is server-side only.** The trust boundary is the FastAPI
layer; the CLI/SDK never carries permission state.

### Per-tool authorization (execution plane)
- `apps/backend/agent/scope.py` — `ToolScopeEnforcer.enforce()` runs on **every**
  third-party tool execution inside `executor.py`'s existing try block.
- Gating is **conditional on ownership**: tasks stamped with
  `created_by_user_id` are always gated; legacy/unowned tasks (internal
  constructions, pre-migration rows) skip the gate, preserving existing
  loop/unit behavior. P1 does not change unowned-task semantics.
- Project authorization reuses `ProjectAuthorizationService
  .authorize_project_access(project_id, user_id, allowed_roles)` — the same
  service the existing agent API uses, so org/project role rules are identical.
- READ vs WRITE/EXECUTE/PUBLISH role sets (`READ_ROLES` / `MUTATE_ROLES`) are
  derived from `tool.required_permission`. Resource targeting:
  - `SearchBenchmarksTool` scopes to the caller's organization.
  - `RunBenchmarkTool` / `GenerateReportTool` resolve the project from the
    benchmark/execution lineage.
  - WRITE/EXECUTE/PUBLISH tools with no resolvable target are denied unless
    anchored to a caller-owned project (`create_benchmark` requires
    `task.project_id`).
- Enforcement is **permission-based, not auto-approved**: a denied tool call
  raises `ToolScopeDenied`, the agent parks the task in `WAITING_FOR_APPROVAL`
  with an `approval_token`, and the run resumes only after server-side approval.

### Session-layer isolation
- `AgentSession.created_by_user_id` stamps every session; every session endpoint
  looks up by owner → cross-user access is HTTP 403, unknown sessions 404
  (no existence leak).
- Listing (`GET /sessions`) filters on `created_by_user_id` (owner-scoped).
- Hosted session tasks are created with **server-set READ-only grants**
  (`granted_permissions=[READ]`) regardless of what a client requests, so a
  session can never mutate without an explicit per-tool approval step.

## 2. Session API contract (implemented)

| Endpoint | Behavior |
|---|---|
| `POST /api/v1/agent/sessions` | Create session + first task (README grant), returns serialized session with transcript |
| `GET /api/v1/agent/sessions` | Owner-scoped list |
| `GET /api/v1/agent/sessions/{id}` | Single session (owner-only) |
| `DELETE /api/v1/agent/sessions/{id}` | Soft-archive → `ARCHIVED`, hidden from list |
| `POST /{id}/messages` | New turn; 409 while `AWAITING_APPROVAL` / `RUNNING` / `WAITING_FOR_EXECUTION`; answers pending clarification when `AWAITING_CLARIFICATION` |
| `POST /{id}/approve` | Validates `approval_token`, grants exactly the tool's permission, resumes |
| `POST /{id}/clarify` | Records answer, resumes into `PLANNING` |
| `POST /{id}/cancel` | Cancels current task |

- State machine: `READY → RUNNING → AWAITING_APPROVAL / AWAITING_CLARIFICATION /
  WAITING_FOR_EXECUTION → COMPLETED / FAILED / CANCELLED`.
- Transcript bounded to 30 messages; per-task assistant append is idempotent.
- Rate limits: task-create (daily) + minute (429 with `Retry-After`) on session
  endpoints, sharing `ApiUsageCounter` with the existing agent API.
- No SSE/streaming; provider defaults to `gemini` (mock in tests).

## 3. SDK additions (P1)

`sdk/python/atlas_sdk`: new `models/sessions.py` DTOs (`AgentSessionRead`,
`AgentSessionTurnRead`, `AgentPendingAction`, `AgentSessionMessage`, and the
three request bodies), 8 `AtlasClient` methods, `models/__init__.py` exports,
`tests/test_sessions.py` (22 cases incl. 401/403/404/409/429/5xx mapping), and
contract-baseline entries. Routing uses open `_get_raw/_post_raw/_delete_raw`
(bare-dict responses), consistent with the execution endpoints; `cli/sdk/`
remains stale and untouched.

## 4. Gate matrix (this session's final run)

| Gate | Command | Result |
|---|---|---|
| Session API tests | `pytest tests/backend/test_agent_sessions.py` | 17/17 pass |
| Scope gate tests | `pytest tests/backend/test_agent_tool_scope.py` | 8/8 pass |
| P0 security regression | `pytest tests/backend/test_agent_api_security.py` | 11/11 pass |
| Combined backend | the three above together | 36/36 pass, 0 fail |
| SDK suite | `pytest sdk/python/tests` | 239 passed, 2 skipped |
| Agent unit suite | `pytest apps/backend/agent/tests` | 105/111 pass; 6 fails all **pre-existing/environmental** (see below) |
| Ruff check (P1 files) | `ruff check <P1 files>` | clean |
| Ruff format (P1 files) | `ruff format --check <P1 files>` | clean |
| Ruff check (repo-wide) | `ruff check .` | 19 errors, **all in `cli/`** — pre-existing on `main` (below) |
| Mypy | `mypy packages` (covers configured sources incl. `apps/backend/agent`, routers) | clean, 236 files |

### Known reds — all pre-existing, not P1-caused
- **Agent suite 6 fails** — reproduced byte-for-byte at `main` (`8a644f7`):
  `test_evaluation_cases.py` (2: `EVALUATION_ERROR` judge/exact_match paths),
  `test_provider_failover.py` (2: tools fed fake IDs like `bm-1` → "badly formed
  hexadecimal UUID string"), `test_wake_on_enqueue.py` (2: `gemini-3.5-flash-lite`
  not configured — no `GEMINI_API_KEY` — and Celery Redis result-store unreachable,
  which also makes the suite take >5 min). Require real provider credentials,
  a Redis backend, and migrated test schema to pass.
- **`ruff check .` 19 errors** — all within `cli/`: untracked junk
  (`cli/packages/`, `cli/sdk/`, egg-info, per repo policy never staged) plus 2
  tracked files byte-identical to `main` (`cli/cli/agent/provider.py`,
  `cli/tests/test_agent_provider.py`).

## 5. Fixes applied in this sprint (working tree, uncommitted)

- `tests/backend/test_agent_sessions.py` — rewritten against confirmed mock
  semantics: fresh READ-only sessions park in `AWAITING_APPROVAL` (never
  `READY`); `_seed_session` defaults `provider="mock"`; task-id filters use
  `uuid.UUID(...)`; clarify/approval tests assert re-park after resume.
- `apps/backend/agent/scope.py` — mypy narrowing (`user_id` non-None), ruff format.
- `apps/backend/agent/executor.py` — `ValueError` guard for unknown tool.
- `apps/backend/routers/agent_sessions.py` — SIM109, task-optional reply guards,
  ruff format.
- SDK session additions (new files + `client.py`/`models/__init__.py`).

## 6. Stop conditions met

- [x] P1 implementation complete per prompt
- [x] New SDK files recorded (no new PyPI deps; no `pyproject.toml` change)
- [x] No docker/Dockerfile changes required by P1
- [x] Gates run (matrix above)
- [x] Web UI compat confirmed: `apps/web/public/agent_ui.js` only calls
      `/api/v1/agent/tasks/*` and `/reports/*` — no route collision with the new
      `/api/v1/agent/sessions/*` router; file untouched.

No push / PR / merge performed. P2 deliberately not started.