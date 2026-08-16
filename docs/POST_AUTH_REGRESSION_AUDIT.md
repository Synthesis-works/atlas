# Post-Auth Regression Audit

> **Date**: 2026-08-16
> **Branch**: `wire_real_llm_adapter`
> **Working directory**: `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter`
> **HEAD at audit start**: `842f6bab5e10149c4cf39a524bdc4e9e0ff2b92e`
> **HEAD at audit end**: see commit section
> **Scope**: Continue the post-auth regression audit that Antigravity stopped at the mock-data / backend phase.

---

## 1. Executive Verdict

**NO REGRESSIONS FOUND. NO APPLICATION CODE WAS CHANGED.**

The post-auth state is stable and healthy:

- All 4 auth & dispatch E2E scenarios passed in a real browser against the canonical stack.
- The dual-origin forensic audit passed with zero divergence between `localhost` and `127.0.0.1`.
- Route audits (static + runtime) passed.
- Frontend production build (`tsc -b && vite build`) succeeded.
- Python test suite: **166 passed, 1 skipped** (skip is a PostgreSQL-only concurrency test), coverage 63%.
- Ruff lint: **All checks passed.**
- Real Groq execution confirmed end-to-end: dispatches return `201`, executions reach `COMPLETED`, and genuine LLM `model_outputs` (real code output, real latency/token counts) are persisted in the canonical DB.
- The `evaluationService.ts` layered 401-handling is **redundant but NOT a regression** — see §4. It was left untouched per instructions (no speculative fixes).

---

## 2. Canonical Environment Confirmation

| Component | Value | Verified |
|---|---|---|
| Canonical worktree | `C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\wire_real_llm_adapter` | ✅ |
| Branch | `wire_real_llm_adapter` | ✅ |
| HEAD (start) | `842f6ba` | ✅ |
| Frontend port 5173 | PID 1508, canonical worktree `node`/Vite | ✅ |
| Backend port 8000 | PID 21236, canonical worktree `.venv` Uvicorn | ✅ |
| No foreign processes on 5173/8000 | confirmed pre- and post-test | ✅ |
| Canonical DB | `<worktree>\atlas_dev.db` | ✅ |
| `.env` | contains API keys; **gitignored, untracked** | ✅ |
| Sensitive/artifact files | `.env`, `atlas_dev.db`, `build/`, `dist/` all ignored | ✅ |

**No modifications were made to `D:\atlas`.**

---

## 3. Runtime & Process Hygiene

Checked `Get-NetTCPConnection -LocalPort 8000,5173` before and after every test run:

- Only canonical-worktree processes ever held ports 8000 and 5173.
- No `D:\atlas` Vite/Uvicorn instance was present.
- The obsolete `D:\atlas\start_frontend.cmd` path was not involved.

---

## 4. `evaluationService.ts` Layered 401 Handling — INVESTIGATION RESULT

### 4.1 What Antigravity flagged

> `evaluationService.ts` contains an additional 401 retry/authentication path layered on top of `client.ts`'s single-flight 401 recovery.

This refers to `dispatchExecution()` and `getExecutionStatus()` in
`apps/landing/src/features/evaluations/services/evaluationService.ts`:

```ts
try {
  res = await apiClient.post<...>(`/api/v1/benchmarks/${benchmarkVersionId}/executions`, payload);
} catch (err: any) {
  if (err?.status === 401) {
    await ensureAuthenticatedSession(true);   // second recovery authority
    res = await apiClient.post<...>(...);      // second manual retry
  } else { throw err; }
}
```

### 4.2 How the two layers actually interact

`client.ts` (`apps/landing/src/core/api/client.ts:143-243`):

1. On a 401 from a protected endpoint, it invokes the **single-flight** `performReAuth()` (one shared login promise).
2. On success it retries the original request **exactly once** with the fresh token.
3. Only if that retry *also* returns 401 does it clear the token and throw `ApiError(401)`.
4. If re-auth itself fails (login HTTP != 2xx, or non-JWT token returned), it clears the token and throws `ApiError(401)`.

`evaluationService.ts` outer catch:

- Fires **only** when `client.ts` has already thrown `ApiError(401)`, i.e. when the backend rejected **both** the original request **and** the single-flight retry.
- In that case it performs its own `ensureAuthenticatedSession(true)` → `loginUser()` and one more POST.

### 4.3 Empirical proof it does NOT misbehave

The `auth-e2e-dispatch.js` Scenario 3 (`Genuinely Invalid JWT → Single-Flight Re-Auth Recovery`) is precisely the stress test for this layering:

- It seeds a structurally-valid but cryptographically-wrong JWT.
- 5 protected requests are rejected with 401 (intentional).
- Result: **exactly 1 login call** (single-flight held), **0 unexpected 401s**, dispatch `201`, execution `COMPLETED`.

This proves the outer `evaluationService` catch **never engaged** during recovery: `client.ts`'s single-flight re-auth + retry succeeded, so `apiClient` never threw the 401 upward. The backend access log corroborates this — only one `POST /api/v1/auth/login` occurred during recovery.

### 4.4 Analysis of theoretical failure modes

| Failure mode | Can it happen? | Evidence / reasoning |
|---|---|---|
| Duplicate authentication (2+ logins) | In the tested recovery path: **No** | Scenario 3 = exactly 1 login call; backend log shows 1 login. |
| Token races (two authorities overwriting `atlas_token`) | **Not demonstrated** | Re-auth and `loginUser` are sequential, not concurrent; both write the same canonical token via `setAuthToken`. The single-flight lock prevents concurrent re-auth. |
| Duplicate requests (double POST) | **Only in a pathological backend state** | The outer catch fires only if a *freshly issued* token is still rejected. That would be a backend-side auth failure, not a client regression. Not observed in any test. |
| Regressions | **None observed** | All 4 E2E scenarios, both forensic origins, routes, build, tests, lint green. |

### 4.5 Verdict on `evaluationService.ts`

- The outer 401 catch is **redundant dead-weight** relative to the single-flight recovery in `client.ts`.
- It is **not** a bug in practice: it never engages in normal recovery because `client.ts` handles 401s first.
- Per instructions, **it was NOT modified**. No speculative cleanup of authentication code was performed.
- **Recommendation (future, non-blocking)**: if the "one canonical auth authority + one controlled recovery mechanism" principle is to be enforced strictly, the outer 401 catch in `evaluationService.ts` could be removed so `client.ts` is the sole recovery authority. This should be a deliberate, separately-reviewed change — not folded into a regression audit.

---

## 5. Test Evidence

### 5.1 `node apps/landing/scripts/auth-e2e-dispatch.js` — PASSED

```
1. Clean Browser:                 ✅ PASSED — JWT valid, 201, COMPLETED, 0 unexpected 401s, 1 login
2. Returning Valid Session:       ✅ PASSED — JWT valid, 201, COMPLETED, 0 login calls
3. Invalid JWT Recovery:          ✅ PASSED — invalid JWT → 1 login call (single-flight) → 201 → COMPLETED
4. Sequential Dispatches (3×):    ✅ PASSED — all 201, 0 unexpected 401s

✨ ALL HARDENED AUTHENTICATION & DISPATCH SCENARIOS PASSED!
```

### 5.2 `node apps/landing/scripts/browser-forensic-test.js` — PASSED (re-run)

- First run: `localhost` navigation hit the 15s `networkidle` timeout during Vite **cold-compile** (first-ever dev load). Marker null; audit failed.
- Re-run (warm): both origins rendered identically:
  - `http://localhost:5173` → `ATLAS_CANONICAL_WORKTREE_MARKER`, RootLen 123212
  - `http://127.0.0.1:5173` → `ATLAS_CANONICAL_WORKTREE_MARKER`, RootLen 123212
- **Zero divergence.**
- Note: the seeded JWT in this script is stale, so 2× HTTP 401 console errors are expected (recovery works). A benign `path d="undefined"` SVG warning appears from a chart component — cosmetic, non-blocking, dashboard renders fully.

### 5.3 `node apps/landing/scripts/test-routes.js` — PASSED (8/8)

### 5.4 `node apps/landing/scripts/runtime-route-check.js` — PASSED (6/6)

### 5.5 Frontend production build — PASSED

`tsc -b && vite build` → 2991 modules, built in 4.52s, `dist/` produced (gitignored).

### 5.6 Python tests — PASSED

`uv run python -m pytest -q` → **166 passed, 1 skipped** (PostgreSQL-only SKIP LOCKED test). Coverage 63% overall.

### 5.7 Ruff — PASSED

`uv run ruff check .` → **All checks passed!**

### 5.8 Mypy — NOT CLEAN (pre-existing, non-auth, out of scope)

`uv run mypy apps/backend packages/database packages/llm` reports **11 pre-existing errors** in 6 files:
`services/billing/gateways/{razorpay,stripe}_provider.py`, `apps/backend/routers/system.py`,
`apps/backend/routers/executions.py`, `apps/backend/routers/evaluation.py`, `apps/backend/main.py`.

None touch auth, the client, or the execution dispatch path. Full-tree mypy also fails on a duplicate-module collision (`services/execution-service/app` vs `services/evaluation-service/app`). **Documented, not fixed** (out of audit scope).

---

## 6. Real Groq Execution & Database Evidence

### 6.1 DB state (`atlas_dev.db`)

- Tables present: 60+ including `executions`, `model_outputs`, `users`, `tasks`, `benchmark_versions`.
- Recent executions (this audit's E2E runs): all `groq/llama-3.1-8b-instant`, status `COMPLETED`.
- `model_outputs` rows: **31** — genuine LLM responses (e.g. `"Here's a simple Python function that adds two numbers..."`), real `duration_ms` (1409–6599), real `tokens_used` (sum 11,501).
- User `demo@atlas.val` present and active.

### 6.2 Real-vs-mock confirmation

- Execution flow is **real**: `AdapterFactory` routes `groq/...` → `RealModelAdapter` → `ProviderAdapter` (Groq client with `GROQ_API_KEY`). Confirmed by genuine output content and latency/token metrics.
- **Mock fallbacks remain only in the frontend catalog layer**, not the execution path:
  - `benchmarkService.ts` returns `MOCK_BENCHMARKS` when the backend returns empty or errors (`getBenchmarks()` catch / empty-array branch).
  - `evaluationService.ts` `getEvaluations()` maps live `/api/v1/executions` DTOs; no mock fallback.
  - Experiments/Providers/Datasets catalogs are presentation-only mock data (`useExperimentCatalog`, `useProviderCatalog`, dataset selectors).

### 6.3 Observations (documented, not regressions)

1. **`completed_at` NULL on COMPLETED executions**: `ExecutionWorker.update_both_status()` (`execution_worker.py:57-62`) sets status directly and bypasses `ExecutionService.update_status()`'s timestamp logic (`executions.py:124-128`). 30/30 recent COMPLETED rows have `completed_at IS NULL`; `started_at` may be set via the same path inconsistently. Frontend synthesizes `completedAt` fallback, so UI is unaffected. **Documented; not changed** (out of audit scope, requires a deliberate worker change).
2. **3 stale QUEUED executions** from `2026-08-16 14:28–14:30` (pre-audit, likely from Antigravity's earlier mock/backend phase). All successful runs since are COMPLETED. Not related to this audit's dispatches.
3. `SAWarning` (leaderboard subquery coercion) in backend log — cosmetic SQLAlchemy 2.0 warning.

---

## 7. Runbook Conformance (`docs/ATLAS_AUTH_DISPATCH_RUNBOOK.md`)

| Runbook invariant | Conformance |
|---|---|
| `POST /auth/login` never receives `Authorization` header | ✅ (`client.ts:175-182`) |
| Single-flight re-auth (one login, not many) | ✅ (Scenario 3 = exactly 1 login) |
| Retry exactly once, clear token if retry 401s | ✅ (`client.ts:204-221`) |
| `atlas_token` always a real 3-segment JWT | ✅ (validated at every step) |
| `local_token_*` impossible to store | ✅ (backend rejects; `setValidatedAuthToken` throws) |
| Protected routes only behind `ProtectedRoute` | ✅ (route audit) |
| Ports 5173/8000 guarded & canonical | ✅ (no foreign processes) |
| Canonical DB in worktree | ✅ |

---

## 8. Files Changed

| File | Change |
|---|---|
| `docs/POST_AUTH_REGRESSION_AUDIT.md` | **Added** — this audit (this commit) |

No application code was modified. No test artifacts, `.env`, DB files, screenshots, logs, or build outputs are committed.

---

## 9. Limitations & Remaining Risks

1. **`evaluationService.ts` redundant 401 catch** remains in place (deliberate). It is dead code in the recovery path today but is a future architectural debt if "one recovery authority" is to be enforced.
2. **Mypy is not green** repo-wide (11 pre-existing errors + duplicate-module collision). Pre-dates this audit.
3. **`completed_at` not populated** by the worker path — affects any future duration-based reporting that relies on `ExecutionService.update_status()` timestamps.
4. **Mock catalog fallbacks** mask backend unavailability in the benchmarks UI (returns mock data instead of surfacing an error). Intentional for now, but could hide real backend outages.
5. **Browser forensic test first-run flake**: `networkidle` can exceed 15s on a cold Vite compile; a warm re-run passes. Suggest a longer navigation timeout or `domcontentloaded` in a future hardening pass.

---

## 10. Final Verdict

> **Post-auth integrity is CONFIRMED. No regressions. No application fixes were required or made.**
>
> - Real Groq execution works end-to-end (login → dispatch 201 → COMPLETED with genuine outputs).
> - Auth recovery is single-flight and correct; the layered `evaluationService` 401 path is redundant but harmless.
> - Environment is canonical; ports are clean; no foreign processes; `D:\atlas` untouched.
> - Audit committed as `audit(atlas): verify post-auth regression integrity` (or similar) and pushed to `origin/wire_real_llm_adapter`.