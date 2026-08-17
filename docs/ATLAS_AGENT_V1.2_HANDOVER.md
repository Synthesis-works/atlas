# ATLAS AGENT V1.2 HANDOVER

Authoritative handover for the **Agent Workspace & Report Export** work. Read this before touching anything in the agent workspace, the agent report pipeline, or the report export endpoint.

---

## A. What the Agent Is

The Atlas Agent is an LLM-driven assistant that can plan and execute benchmark evaluation work inside the Atlas platform. It:

1. Receives a goal (e.g. "run Basic Subtraction Benchmark").
2. Resolves the benchmark, selects a primary provider, and routes through fallback providers on failure.
3. Executes benchmark cases, persists model outputs + evaluation results, and generates a **ReportVersion** (the persisted report artifact).
4. Tracks its own lifecycle in an **in-memory task store** (`_agent_tasks_db` in `apps/backend/routers/agent.py`).

Important architectural fact: **Agent task state is in-memory only** (per backend process). The **report artifact is persisted** in SQLite (`atlas_dev.db`). After a backend restart, agent task history is lost but reports/executions remain queryable.

## B. Architecture

- FastAPI backend (`apps/backend`), Vite React frontend (`apps/landing`), shared domain services in `services/report`.
- Report domain services (Repository Pattern) live in `services/report/{models,repositories,services,exporters,core}`.
- Agent execution logic lives in `apps/backend/agent` (providers, tools, state, tests).
- API routes decouple DB schemas via Pydantic read models (`services/report/models/read_models.py`, `apps/backend/schemas/*`).

## C. Frontend Routes

- `/dashboard/agent` — workspace (run list from task store, New Run, ProviderPanel).
- `/dashboard/agent/run/:taskId` — run detail (status, timeline, download, inspect, clarify/approve cards).
- `/dashboard/agent/report/:reportId` — the persisted report page (IA rewrite done in V1.2).

## D. Backend Routes (agent)

- `GET  /api/v1/agent/providers` — available providers + status.
- `POST /api/v1/agent/tasks` — start a new agent task (runs on the FastAPI thread; see H).
- `GET  /api/v1/agent/tasks` — list in-memory tasks.
- `GET  /api/v1/agent/tasks/{task_id}` — task detail (status, trace, steps, tool calls).
- `POST /api/v1/agent/tasks/{task_id}/approve|cancel|clarify|run-again`.
- `GET  /api/v1/agent/tools` — tool registry.
- `GET  /api/v1/agent/reports/{report_id}` — persisted report payload (report_version-scoped read model).

## E. Reporting Routes (shared domain)

- `GET /api/v1/reports/runs` — paginated run summaries (`{items, total, page, size}`).
- `GET /api/v1/reports/runs/{run_id}` — run summary.
- `GET /api/v1/reports/runs/{run_id}/export?format=json|csv&include_prompt=&include_expected_output=` — **report artifact export** (see L).

## F. Authentication Flow (dev)

- `POST /api/v1/auth/login` with `{username: "admin@example.com", password: "password123"}` → `{success, data: {access_token}}`.
- All protected routes use `Authorization: Bearer <token>`. Frontend auto-logs-in in dev via `ensureAuthenticatedSession` (real JWT flow).
- `require_permission("report:read")` on the export endpoint must **never** be removed or made public.

## G. Providers & Fallback

- Chain order: **gemini → groq → mistral** (configured in the provider router).
- Router emits trace events: `provider_decision_<name>` (details: `provider`, `model`, `attempt`, `latency_ms`, `decision_type`) and `provider_fallback` (details: `failed_provider`, `next_provider`, `reason`).
- `next_provider` is `"NONE"` when no fallback remains. The UI renders these as routing badges in the timeline.
- Free-tier Gemini quota is frequently exhausted (429). Live runs fall back to groq/mistral. Gemini quota does not block the app.

## H. Execution Model

- Runs execute **synchronously on the FastAPI request thread** (not via Celery/EventBus). Acceptable for the agent workspace; do NOT silently change to Celery without a design review.
- Each task may create one or more `Execution` rows + one `ReportVersion`.
- `task.execution_ids` links a task to its execution UUIDs (stored as strings).

## I. Lifecycle & State Management

- Statuses: `pending → running → clarification/approval → completed | failed | cancelled`.
- `AgentTask` tracks `step_count`, `total_tool_calls`, `execution_trace`, `started_at`, `completed_at`, `primary_provider`.
- `_agent_tasks_db: dict[str, AgentTask]` is process-local; cleared on restart. The UI degrades gracefully to empty workspace after restart.

## J. Run History & Concurrency

- The workspace lists tasks from `_agent_tasks_db`. No long-term task history table exists (in-memory by design; documented limitation).
- Concurrent runs are possible but each is sequential internally. No locking issues observed; keep the store dict operations simple.

## K. UI Components (V1.2 rewrite)

- `status.tsx` — reusable status system (`AgentStatusBadge`, `statusTone`, `getStatusLabel`). Default fallback: `"Unknown"`.
- `AgentTimeline.tsx` — semantic step colors (GREEN=success, BLUE=working/pulse, YELLOW=attention, RED=failed/stopped, GRAY=neutral; purple = brand only), provider routing badges, latency, tool call + observation summaries with collapsible raw payloads.
- `AgentSidebar.tsx` — status icons, `GROUP_DOT` colored group headers, pulsing blue active run dot.
- `AgentWorkspaceRun.tsx` — completed/failed/stopped cards, `AgentStatusBadge`, Download button.
- `AgentReportPage.tsx` — full report IA (header, summary, results, execution, benchmark, metadata sections) + Download Report button.
- `AgentClarificationCard.tsx` — yellow "Action Required" + Continue.
- `AgentApprovalCard.tsx` — attention-tone aligned.

## L. Report Export (V1.2 fix — READ FIRST)

**Original bug:** `GET /api/v1/reports/runs/{run_id}/export` returned `[]` (2 bytes) for agent-created runs.

**Root cause:** the export dumped per-case `ModelOutput` rows via an `INNER JOIN` on execution_id. Agent runs created `Execution` + `ReportVersion` rows but **zero** `model_outputs` rows, so the dump was an empty list. It never exported the actual persisted report.

**Fix (implemented):**
- New export read models in `services/report/models/read_models.py`: `ReportExportReportRead`, `ReportExportExecutionRead`, `ReportExportBenchmarkRead`, `ReportMetricExportRead`, `ReportExportRead`.
- `JSONExporter` now accepts a single `dict`/`BaseModel` payload (not just iterables).
- `ExportResult` gained optional `filename_stem`; endpoint uses it for `Content-Disposition` (`<title>-v<version>.json`, else `run_{run_id}.json`).
- `ReportingRepository.get_report_export(run_id)` resolves `(Execution, ReportVersion, Report, BenchmarkVersion, Benchmark, [ReportMetric])`. Returns `None` if execution missing.
- `RunQueryService.get_report_export(...)` composes the document and merges optional truthful `execution_meta` (steps, tool_calls, provider_chain, duration, status).
- `ReportingService.build_report_export(...)` + `export_run_results(..., execution_meta=None, document=None)`. CSV remains row-based (`document.results`).
- Router: `_collect_agent_execution_meta(run_id)` lazily imports `_agent_tasks_db` from `apps.backend.routers.agent` and builds the provider chain from real trace events. Returns `{}` when no task matches.

**Truthfulness rules (do not break):** metrics come from real `ReportMetric` rows (empty `[]` when none); benchmark is `null` when the execution's `benchmark_version_id` is dangling; timestamps/duration come only from real DB values (null when absent); provider_chain/steps/tool_calls only from the live agent task store. Never fabricate.

## M. Report Page & Download

- Report page fetches `GET /api/v1/agent/reports/{report_id}`; renders honest empty states ("No numeric metrics recorded", "No benchmark resolved").
- Download button on both run and report pages uses `downloadExecutionReport(execId, 'json')` (frontend `agentService`) → export endpoint → saves blob with returned filename.

## N. Telemetry & Colors

- Semantic status tones are the source of truth: GREEN=success, BLUE=working, YELLOW=attention, RED=danger/failed/stopped, GRAY=neutral.
- Execution trace events drive the timeline. Latency from `latency_ms` in `provider_decision_*` details.

## O. Tests

Backend (run from repo root or `apps/backend`, always with `-o addopts=""`; plain pytest fails because pyproject `addopts` uses `--cov` without pytest-cov installed):

```
python -m pytest apps/backend/agent/tests/test_report_integrity.py apps/backend/agent/tests/test_agent_core.py apps/backend/agent/tests/test_report_export.py -q -o addopts=""
python -m pytest tests/backend/test_api_reporting.py services/report -q -o addopts=""
```

- `test_report_export.py` — NEW regression suite: real artifact export, truthful nulls for dangling benchmark, agent execution_meta merge, empty-meta fallback.
- `test_api_reporting.py` — endpoint tests (export tests now assert `execution_meta={}`, `document=None` kwargs).

Frontend: `npx tsc -b`, `npm run build`, `npx oxlint` (in `apps/landing`). 0 errors; warnings are pre-existing.

## P. Known Limitations (backend)

- Agent task state is in-memory; workspace history disappears on backend restart.
- No live FAILED/CANCELLED/clarification task fixtures — validation used the 3 persisted COMPLETED runs + regression tests.
- No `ReportMetric` rows exist for persisted runs → metrics export as `[]` (truthful).
- Benchmark linkage for persisted runs is genuinely dangling (`benchmarks` table empty; execution `benchmark_version_id` matches nothing) → `benchmark: null` (truthful).
- `started_at`/`completed_at` NULL on persisted executions → `duration: null` (truthful).
- Execution DB status for the sample run is `FAILED` even though the agent task was COMPLETED — two different truth sources (task store vs DB execution row). The export reports the DB execution status.
- Unrelated pre-existing backend test failures out of scope: `test_evaluation_cases.py` collection error (`cannot import name '_benchmark_execution_store'`), `test_provider_failover.py`, execution-domain tests.
- Gemini free-tier quota 429 → live runs use groq/mistral.

## Q. Worktree / Branch

- Branch: `implement_atlas_agent_loop`
- Worktree path: `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\implement_atlas_agent_loop`
- Main repo root: `D:\atlas` (do not confuse the two; the live backend runs from the worktree).
- DB: `atlas_dev.db` at the worktree root (SQLite). UUIDs are stored **without dashes** in SQLite; the API returns dashed UUIDs.

## R. Live Services

- Backend: `python -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000` **from the worktree root** (cwd matters: `.env` sets `DATABASE_URL=sqlite:///./atlas_dev.db` relative to the root; launching from any other cwd connects to the wrong/empty DB and login 401s).
- Frontend: `npm run dev` in `apps/landing` on `:5173`.
- Edge CDP debugging on `127.0.0.1:9333` for E2E scripts in `%TEMP%\opencode`.

## S. Files Changed (this pass)

Backend:
- `services/report/models/read_models.py` — export read models.
- `services/report/exporters/base.py` — `ExportResult.filename_stem`.
- `services/report/exporters/json_exporter.py` — dict/BaseModel payload support.
- `services/report/repositories/reporting_repo.py` — `get_report_export`.
- `services/report/services/queries.py` — `RunQueryService.get_report_export`.
- `services/report/services/reporting.py` — `build_report_export`, `export_run_results` kwargs, `_slugify`.
- `apps/backend/routers/reporting.py` — export endpoint + `_collect_agent_execution_meta`.

Tests:
- `apps/backend/agent/tests/test_report_export.py` — new regression suite.
- `tests/backend/test_api_reporting.py` — updated export endpoint assertions.

Docs:
- `docs/ATLAS_AGENT_V1.2_HANDOVER.md` — this file.

## T. Verification Commands (quick smoke)

```powershell
# backend up?
Get-NetTCPConnection -LocalPort 8000 -State Listen

# login + export a real report
python -c "import urllib.request,json;base='http://127.0.0.1:8000/api/v1';req=urllib.request.Request(base+'/auth/login',data=json.dumps({'username':'admin@example.com','password':'password123'}).encode(),headers={'Content-Type':'application/json'},method='POST');tok=json.load(urllib.request.urlopen(req))['data']['access_token'];req2=urllib.request.Request(base+'/reports/runs/2793f045-7550-41ae-8c81-edbd6eb4e246/export?format=json',headers={'Authorization':'Bearer '+tok});print(urllib.request.urlopen(req2).read().decode()[:300])"
```

Expected: a JSON document with `report.title == "Basic Subtraction Benchmark Report"`, `report.version == "1.0.0"`, `execution.id`, `benchmark == null`, `metrics == []`.

## U. DO NOTs

- Do NOT recreate the agent workspace UI or report page without reviewing this doc and the V1.2 IA.
- Do NOT reintroduce mock providers or hardcoded provider data.
- Do NOT fabricate metrics, benchmarks, timestamps, or durations in the export.
- Do NOT bypass auth on the export endpoint.
- Do NOT overwrite uncommitted work in the worktree.
- Do NOT revert the Dockerization-era migration fixes (`3a1cf533642c`, `2256bd2b7c2c`).

---

## NEXT AGENT INSTRUCTIONS

1. Read this document fully.
2. `git status` + `git log --oneline -10` in the worktree to see current state before changing anything.
3. Start backend from the worktree root (`python -m uvicorn apps.backend.main:app --host 127.0.0.1 --port 8000`) and frontend (`npm run dev` in `apps/landing`).
4. Verify: `GET /api/v1/agent/providers`, workspace at `/dashboard/agent`, run page, report page at `/dashboard/agent/report/fa1dc829-8088-4e0b-868f-8c67eee0ce01`, and the export per section T.
5. Run the test suites in section O before and after any change.
6. If documentation conflicts with source code, identify the conflict, explain it, and propose a resolution before acting.
