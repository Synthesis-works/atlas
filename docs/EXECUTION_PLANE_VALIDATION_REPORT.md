# Execution Plane Validation Report

Branch: `feature/docker-execution-runtime` (5 commits on `4d563bf`)
Run: [32581407965](https://github.com/Synthesis-works/atlas/actions/runs/32581407965) — 2026-08-22, **conclusion: success**

## 1. REAL REMOTE EVIDENCE (GitHub-hosted runner, ubuntu-24.04)

Executed by `.github/workflows/benchmark-execute-dryrun.yml`, zero secrets used:

| Step | Result |
| --- | --- |
| Service postgres:15 healthy | OK |
| `docker build` of pinned benchmark image on runner | OK |
| Negative control: no provider keys in runner env | OK (0 leaked) |
| Seed synthetic execution | `execution_id=a956474c-de23-4355-9e06-7c4cd2a3e201` |
| Production code path (`ENVIRONMENT=production`) | `executor_type=docker` selected |
| Startup reaper | `attempts_reaped=0 executions_requeued=0` |
| Verify | `status=COMPLETED container=96c39df9884d digest=sha256:78f3d4bdf3073… outputs=1` |
| Idempotency (no duplicate ModelOutputs) | passed |
| Orphan containers after run | 0 |

This proves end-to-end on real infrastructure: production executor selection →
isolated Docker container → provenance persistence (container id, image digest,
exit code, termination reason) → outbox events → cleanup.

## 2. LOCAL EVIDENCE (Docker Desktop, Windows)

- Real-container proof run: exit 0 (`52d478665121`), offline smoke PASSED.
- Level-2 dry-run replica against local postgres:15: identical verify output,
  `container=e7b1fcb9e056`, digest recorded.
- Test suites: backend 119 passed (d7 excluded — requires live postgres, pre-existing),
  integration 10 passed/1 skipped, ruff + mypy clean.

## 3. Credential-exposure audit (2026-08-22)

Method: all 13 non-trivial `.env` values were loaded in-memory and searched for
(exact-match) across: every tracked file, the full PR diff (`4d563bf..HEAD`),
all 8 branch commit patches, the GitHub Actions logs of runs 32581407965 /
32581751584 / 32582036540 / 32582038566, and local tooling outputs. Generic
high-signal patterns (Google `AIza…`, OpenAI `sk-…`, `xai-…`, GitHub PAT,
AWS AKIA) were scanned over the same corpora. No secret value was printed
during the audit.

| Corpus | Result |
| --- | --- |
| Tracked files (working tree) | CLEAN |
| PR diff + all 8 commit patches | CLEAN |
| All 4 GitHub Actions logs | CLEAN |
| `.env` tracked in any reachable history | NEVER (only `.env.example`) |
| Repo/Actions variables & secrets | zero variables, zero secrets configured |
| Local dev-server logs (`%TEMP%\opencode\atlas-backend.out.log`, `backend_stdout.log`) | **GEMINI_API_KEY present — local machine only** |

Findings:
1. **No real secret was ever committed, pushed, or rendered into an Actions
   log or artifact.** Nothing on GitHub requires rotation.
2. `GEMINI_API_KEY` appears in **local-only** dev-server stdout logs and once
   in a local pytest failure diff (console only). These never left the
   developer machine; rotation is optional hygiene, not incident response.
   Follow-up (out of PR scope): locate the backend code path that prints
   settings/env to stdout at startup and redact it.
3. The dry-run workflow uses a throwaway `JWT_SECRET` literal that grants
   nothing; `DATABASE_URL` was auto-masked by Actions.

## 4. NOT TESTED / KNOWN GAPS

- **Real provider traffic**: mock target only. No API keys were ever present.
- **Celery + Redis dispatch**: driver invokes `ExecutionWorker.process()`
  directly; broker round-trip not exercised remotely.
- **GHCR publishing**: image is built per-run, not pulled from a registry.
- **`repository_dispatch` trigger**: only fires for workflows on the default
  branch; same limitation hit for `workflow_dispatch` (HTTP 404). The dry-run
  therefore triggers via scoped `push` to this branch until merged to main.
- **Production enablement** (`BENCHMARK_EXECUTION_ENABLED=true`): intentionally
  not set; awaits ToS/public-log review decision.

## 5. Security-review status (HIGH findings)

| ID | Finding | Status |
| --- | --- | --- |
| H-1 | Production silently falls back to LocalExecutor | Fixed — `executor.py` `get_default()` raises `ExecutorUnavailable`; runner raises on explicit registry miss; regression-tested (16 selection tests) |
| H-2 | Reap window shorter than Celery hard-time limit | Fixed — reap window 120 min > 62-min max runtime, asserted at import; tested |
| H-3 | `${{ }}` shell interpolation in execute workflow | Fixed — inputs passed via env vars, never inline-expanded; dry-run workflow uses the same pattern |
| H-4 | Reaper strands requeued executions (no outbox row) | Fixed — reaper emits `ExecutionQueuedEvent` outbox row in same transaction; tested |

## 6. Merge readiness

All HIGH/MEDIUM findings from `PRE_MERGE_SECURITY_REVIEW.md` are fixed with
regression tests. Final suite: backend **123/123 passed** (with live
postgres), docker integration **10 passed / 1 skipped**, ruff clean,
mypy clean. Remaining before enabling real traffic: policy decision on
GitHub Actions as the permanent execution plane (ToS/public-log review),
then set `BENCHMARK_EXECUTION_ENABLED=true`. Remote benchmark execution
remains **disabled**.

