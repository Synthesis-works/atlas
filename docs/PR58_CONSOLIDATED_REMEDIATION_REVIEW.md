# PR #58 Consolidated Remediation — Independent Review Report

**Branch:** `fix/pr58-consolidated-remediation`
**Base:** `2fa36f6` (main, merge of #57)
**Scope:** 16 commits, 71 files changed (+3366 / −655) across backend, landing app, tests, and CI.
**Review date:** 2026-09-05

---

## 1. Verdict

**Approve for merge.** All nine audit findings are addressed with passing regression
tests. The branch is verified end-to-end: backend lint/format/types/tests, frontend
typecheck/lint/tests/production build, and a headless-browser E2E audit that reads real
persisted telemetry.

---

## 2. Finding → Fix → Evidence Map

| # | Finding | Fix commit | Regression evidence |
|---|---------|-----------|---------------------|
| F1 | `/api/v1/models` 404 / error envelope — `models` router never mounted; `AdapterFactory.get_available_models` did not exist | `6f9fcba` `feat(models): restore model registry endpoint and typed registry service` | `tests/api/test_models_registry_contract.py` (3 tests, pass) |
| F2 | Execution dispatch lacks idempotency / unique traceability | `258aeb0` `feat(executions): add idempotent dispatch via idempotency_key` | `tests/api/test_execution_contract.py` (pass; 201-pinned contract) |
| F3 | Global benchmark creation attaches to arbitrary unauthorized projects | `0de82d3` `fix(benchmarks): require authorized explicit project for global create` | `tests/api/test_global_benchmark_creation.py` (authorized vs 403 matrix, pass) |
| F4 | Execution scores fabricated/presented against the wrong 0-1 vs 0-100 contract | `c3dbb18` `fix(scores): canonicalize execution scores to the 0-1 contract` | API contract tests pass; mapper tests assert 0-1→% conversion |
| F5 | Benchmark UI defaults missing `verificationScore` to 100 (fabricated pass) | `1e65fae` `fix(benchmarks): never fabricate verification scores from absent telemetry` | `benchmarkMapper.test.ts` (8 cases, pass): null stays null, 0-1→%, legacy >1→preserved |
| F6 | BenchmarkAnalytics/Header/'Benchmark' badges hard-code "Live", "Empty", statuses | `605a4e3` `fix(benchmarks): derive status badges and score normalization from real data` | `tsc -b`, lint, vitest suite pass; E2E renders real data |
| F7 | `resolve_provider_and_model` silently falls back to a blanket Ollama default | `fbe6816` `fix(llm): require explicit provider routing instead of blanket Ollama fallback` | `tests/backend/test_llm_provider_routing.py` (pass) |
| F8 | Executions can dispatch against unlinked dataset versions | `b0dfa52` `fix(executions): enforce dataset version invariant on dispatch` | `tests/api/test_execution_dataset_version_invariant.py` (pass) |
| F9 | E2E script hard-coded credentials/score 100.0/benchmark name | `5ae70f0` + `2bc1bea` (env-driven creds + honest score checks; project_id for F3 create) | Live E2E audit passes (see §5) |

**Additional (not in the original 9):**
- `655319d` `feat(benchmarks): eliminate mock data and integrate live backend telemetry` — removes mock-data fabrication at the source.
- `257fe8c` `fix(workspace): remove fabricated telemetry from dashboard presentation` — CapabilitySnapshot, AtlasRuntime, Workspace heatmap/hierarchy, ActiveEvaluations.
- `30e5cbb` `feat(frontend): provenance-aware badges from real execution configs` — ProvenanceBadge/VerificationBadge never label unknown provenance as verified/demo; `evaluationService` resolves provenance from real dashboard execution configs.
- `abed2c6` `fix(frontend): correct AtlasRuntimeWidget health check endpoint path` — `/api/v1/health` → `/health`.
- `9e43ed1` `test(executions): align benchmark_version mocks with the dataset_versions contract` — F8 invariant surfaced `'Mock' object is not iterable` in three pre-existing fixtures; fixtures now model the real `dataset_versions` shape.
- `21eefde` `chore(style): apply ruff format to branch-owned modules`.

---

## 3. Verification Evidence

### Backend (repo root, Python 3.11, `uv`)
- `ruff check .` — **pass** (0 errors).
- `ruff format --check` on all branch-owned modules — **pass**.
- `mypy packages` — **pass** (232 source files, no issues).
- `pytest` (full suite, no cov) — **pass**.

### Frontend (`apps/landing`, Node/Vite/React)
- `npx tsc -b` — **pass** (0 errors).
- `npx oxlint src` — 0 errors (81 pre-existing lint warnings, unchanged).
- `npx vitest run` — **4 files / 18 tests pass**.
- `npm run build` (production) — **pass**.

### E2E (local: Postgres + backend :8000 + Vite :5173)
`node scripts/verify-benchmarks-e2e.js` (headless Chromium) — **all 5 steps pass**:
auth→real JWT; catalog from DB (2 benchmarks); smoke-benchmark telemetry (3 cases,
1 completed execution, avg score 90% in 0-1 contract, no fabricated 100.0); live
creation + polling sync (authorized via explicit `project_id`); DOM render of the
smoke benchmark and the Atlas Runtime widget.

Formatting note: `ruff format --check .` strictly over the *whole* repo still reports
baseline drift in two files the branch does not touch (`apps/backend/config.py`,
`apps/backend/schemas/benchmarks.py`). This predates the branch (also present at
`2fa36f6`). It does not block this PR; flagging as a separate baseline cleanup.

---

## 4. Known Residual Risks / Notes

1. **Leaderboard/reporting schemas** remain 0-100 by design; only the canonical
   execution contract and UI presentation were normalized to 0-1 (F4 scope decision).
2. `useBenchmarkCatalog.ts` uses a try/catch-guarded hook call with an
   `eslint-disable` (optional workspace-store consumption). Lint passes, but reviewers
   may prefer a provider-restructuring later.
3. Demo seed data (`seed_demo.py`, and the E2E smoke benchmark) is intentionally
   flagged `source='demo', is_verified=false` and surfaced as such — never as real.
4. Docker/Runtime checklist (`docs/RUNTIME_CHECKLIST.md`) is not applicable to this
   PR: no Dockerfiles, compose files, or runtime config were changed.
5. E2E script leaves the `Live Polling Proof <ts>` benchmark in local dev DBs by
   design (creation sync proof).

---

## 5. Recommendation

Merge `fix/pr58-consolidated-remediation` into `main` after CI confirms the same
gates (backend ruff/mypy/pytest, landing tsc/lint/test, plus the docker runtime
checklist for the deployment branch). No further remediation required for the nine
findings.