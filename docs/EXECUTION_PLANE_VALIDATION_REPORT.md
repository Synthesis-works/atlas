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

## 3. NOT TESTED / KNOWN GAPS

- **Real provider traffic**: mock target only. No API keys were ever present.
- **Celery + Redis dispatch**: driver invokes `ExecutionWorker.process()`
  directly; broker round-trip not exercised remotely.
- **GHCR publishing**: image is built per-run, not pulled from a registry.
- **`repository_dispatch` trigger**: only fires for workflows on the default
  branch; same limitation hit for `workflow_dispatch` (HTTP 404). The dry-run
  therefore triggers via scoped `push` to this branch until merged to main.
- **Production enablement** (`BENCHMARK_EXECUTION_ENABLED=true`): intentionally
  not set; awaits ToS/public-log review decision.

## 4. Merge readiness

All HIGH/MEDIUM findings from `PRE_MERGE_SECURITY_REVIEW.md` are fixed with
regression tests. Remaining pre-merge actions: PR review, and a policy decision
on enabling real benchmark traffic.
