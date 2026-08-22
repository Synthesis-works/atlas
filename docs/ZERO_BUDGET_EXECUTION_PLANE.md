# Zero-Budget Execution Plane Investigation

**Branch:** `feature/docker-execution-runtime`
**Date:** 2026-08-21
**Constraint:** Budget is **₹0**. Paid infrastructure must not be the default recommendation.
**Status:** Investigation only. Nothing provisioned, nothing changed.
**Predecessors:** `PRODUCTION_EXECUTION_PLANE_AUDIT.md`, `PRODUCTION_READINESS_PLAN.md`

---

## Evidence Standard

- **[VERIFIED-DOC]** — from official provider documentation (linked).
- **[VERIFIED-LOCAL]** — checked against this machine/repo directly.
- **[REPORTED]** — third-party/community reporting; treat with lower confidence.
- **[RECOMMENDATION]** — my assessment.

---

## Headline Finding [VERIFIED-LOCAL]

```text
$ gh repo view --json visibility,isPrivate,nameWithOwner
{"isPrivate": false, "nameWithOwner": "Synthesis-works/atlas", "visibility": "PUBLIC"}
```

**The Atlas repository is public.** This changes everything: GitHub-hosted standard
runners are *free and unlimited* for public repositories — no minutes meter at all.

---

## Option 1 — GitHub Actions Public-Repo Runners ⭐ RANK 1

### Facts [VERIFIED-DOC]

| Property | Value | Source |
|---|---|---|
| Cost for public repos | **Free & unlimited** standard-runner minutes | docs.github.com/actions/concepts/billing-and-usage |
| Linux runner spec | **4 vCPU / 16 GB RAM / 14 GB SSD** (`ubuntu-latest`) | docs.github.com/actions/reference/runners/github-hosted-runners |
| Concurrency (Free plan) | 20 concurrent jobs | docs.github.com/actions/reference/limits |
| Job timeout | 6 hours/job | docs.github.com/actions/reference/limits |
| Docker Engine | Preinstalled on runners; full sibling-container support | standard runner image |
| External trigger | `POST /repos/{owner}/{repo}/dispatches` with `repository_dispatch`; fine-grained PAT needs `contents:read+write`, `metadata:read`; payload in `client_payload` | docs.github.com/rest/repos/repos + peter-evans/repository-dispatch docs |
| Constraint | Dispatch-triggered workflow **must live on the default branch** | same |

### How Atlas would use it [RECOMMENDATION]

```text
API commits execution → outbox (unchanged)
        │
        ▼
Dispatcher (tiny cron or existing worker) ──► POST /repos/Synthesis-works/atlas/dispatches
        │                                      client_payload={"execution_id": "..."}
        ▼
Workflow on main:  on: repository_dispatch (types: [benchmark-execute])
   ├─ checkout repo
   ├─ python script: load execution payload from Supabase
   ├─ run DockerExecutor  ← UNCHANGED CODE, real Docker Engine on runner
   ├─ write ModelOutputs + benchmark_execution_attempts back to Supabase
   └─ job ends; runner VM destroyed
```

- **Executor compatibility:** `DockerExecutor` works **unchanged** — runners expose a full Docker Engine. No new executor class needed.
- **Isolation:** each job gets a fresh ephemeral VM that is destroyed afterward — *stronger* hygiene than a long-lived runner host.
- **Secrets:** provider keys + Supabase URL stored as Actions secrets; automatically masked in logs; injected into the benchmark container only via the existing `_provider_env()` allow-list.
- **Results path:** direct write-back to Supabase over TLS 5432 (outbound). No artifacts needed for MVP.

### Risks / limitations

1. **ToS gray area [HONEST FLAG]:** GitHub's additional terms restrict Actions to building/testing/deploying the repository's own software. Running your app's workload is a gray zone widely practiced for cron-style jobs; at MVP volume (minutes/day) enforcement risk is low but non-zero. Mitigation: keep volume modest; the workflow genuinely checks out and exercises this repo's code, which supports the "testing this project's software" framing.
2. **Public logs:** workflow logs on a public repo are world-readable. Never echo `DATABASE_URL`; rely on Actions secret masking; benchmark prompts/outputs will be visible (acceptable if benchmarks are public-by-design — decide explicitly).
3. **Latency:** dispatch→job-start is typically seconds to ~1 min (queue + VM boot). Fine for benchmarks, wrong for interactive use cases.
4. **PAT management:** one fine-grained PAT scoped to this single repo, held by the control plane as a secret. Revocable instantly.
5. **No always-on process:** pure request-driven; there is no daemon to reap stale attempts — the workflow itself marks stale attempts on start (reuses planned reaper logic).

---

## Option 2 — Oracle Cloud Always-Free ARM VM — RANK 2

### Facts [VERIFIED-DOC + REPORTED]

| Property | Value | Source |
|---|---|---|
| Allowance | **2 OCPU / 12 GB RAM** ARM64 (Ampere A1), pooled per tenancy; ~200 GB block storage; 10 TB egress | docs.oracle.com Always Free Resources |
| ⚠️ Halved June 15, 2026 | Was 4 OCPU/24 GB; cut without announcement | infoq.com/news/2026/07/oracle-cloud-free-tier-limits [REPORTED] |
| Signup requirement | Credit/debit card for identity verification (no charge) | oracle.com/cloud/free |
| Capacity | "Out of host capacity" common in popular regions (Mumbai starved); retry loops / smaller shapes help | community-documented [REPORTED] |
| Idle reclaim | Instances reclaimed if 7-day p95 CPU, network, **and memory** all < 20% | docs.oracle.com / community [REPORTED] |
| Docker | Full Engine on Ubuntu 24.04 ARM64; python:3.11-slim has arm64 variant; httpx/pydantic are pure-Python ⇒ image is arch-neutral | standard practice |

### Assessment [RECOMMENDATION]

A genuine always-on VM running today's worker + `DockerExecutor` **unchanged**. But three frictions:

1. **Card required at signup** — if you have no payment card at all, this option is dead on arrival [HUMAN blocker].
2. **Capacity roulette** — you may fight "out of host capacity" for days; Mumbai is among the worst regions.
3. **Idle-reclaim tension** — a benchmark runner is mostly idle; sustained <20% p95 across all three metrics for 7 days risks reclamation. Real periodic executions clear it, but a quiet week could cost you the instance.

2 OCPU/12 GB comfortably fits concurrency 1–2 under our 2-core/2 GB-per-container defaults.

---

## Option 3 — Vercel Sandbox Hobby — RANK 3

### Facts [VERIFIED-DOC]

| Property | Value | Source |
|---|---|---|
| Free allotment | 5 hrs **Active CPU**/mo; 420 GB-hrs provisioned memory/mo; 5,000 creations; 20 GB transfer | vercel.com/docs/sandbox/pricing |
| Per-sandbox resources | up to 4 vCPU / 8 GB (2 GB RAM per vCPU), 32 GB NVMe | same |
| Session limit | **45 min** max session (Hobby); default timeout 5 min, extendable | same |
| Concurrency | 10 concurrent sandboxes | same |
| Isolation | Firecracker microVM, designed for untrusted code; credential brokering keeps secrets outside sandbox | vercel.com/sandbox |
| Docker Engine inside | ❌ None — microVM is user-space only | platform design |

### Assessment [RECOMMENDATION]

Architecturally elegant — the microVM *is* the untrusted-code boundary, exactly matching our threat model — but requires a **new executor** (`VercelSandboxExecutor`) that runs `container_entry.py` directly in the sandbox instead of launching a nested container. The `Executor` interface accommodates this cleanly (that was its purpose).

Two constraints:
- **45-minute session cap** vs our 30-min default execution timeout: workable but tight; timeouts must be tuned.
- **5 hrs Active CPU/month**: favorable because Active-CPU billing excludes I/O wait — LLM-bound benchmarks spend most wall-clock awaiting provider responses. Rough budget: ~60–150 executions/month depending on CPU share. Fine for MVP validation, thin for growth.

---

## Option 4 — Your Own PC (temporary) — RANK 4

[VERIFIED-LOCAL] Docker Desktop on this machine already ran the real-container proof (`52d478665121`, exit 0).

- ₹0, zero signup, full Docker Engine, code unchanged.
- Limits: PC must stay awake; home IP reliability; sleep kills mid-run attempts (mitigated later by the stale-attempt reaper).
- Best used as the **validation week** step before committing to any remote option.

---

## Option 5 — Render Free Tier — ❌ RULED OUT

[VERIFIED-DOC] render.com/docs/free + /docs/service-types:

- Free instance: **512 MB RAM / 0.1 CPU** — cannot even hold the worker comfortably, let alone Docker.
- No Docker Engine / privileged mode on any Render runtime ⇒ no sibling containers.
- Spin-down after 15 min idle; no persistent disks; no shell access; no one-off jobs on free.

There is no honest way to make Render free tier execute Docker-isolated benchmarks.

---

## Comparison Matrix

| Criterion | GH Actions (public) | OCI Always-Free | Vercel Sandbox Hobby | Home PC | Render Free |
|---|---|---|---|---|---|
| ₹0 eligible | ✅ unlimited | ✅ (card needed) | ✅ quota-limited | ✅ | ✅ |
| CPU/RAM | 4 vCPU/16 GB | 2 OCPU/12 GB | ≤4 vCPU/8 GB | varies | 0.1/512 MB |
| Max run | 6 h/job | unlimited | 45 min/session | unlimited | spin-down 15 min |
| Docker Engine | ✅ native | ✅ native | ❌ (microVM instead) | ✅ | ❌ |
| `DockerExecutor` unchanged | ✅ | ✅ | ❌ new executor | ✅ | n/a |
| Persistence | ephemeral/job | disk persists | snapshot-based | local disk | none |
| Networking | outbound only | outbound (+optional ingress) | outbound + ports | home NAT | restricted |
| Secrets | Actions secrets (masked) | VM env file | Vercel brokered | local .env | env vars |
| Concurrency | 20 jobs | 1–2 (sized) | 10 sandboxes | 1–2 | 1 |
| Isolation quality | fresh VM per job ✅✅ | shared kernel ⚠️ | Firecracker ✅✅ | shared kernel ⚠️ | none |
| Setup effort | Low-Med (workflow + PAT) | Med-High (signup/capacity) | Med (new executor) | Trivial | — |
| Main risk | ToS gray area; public logs | card gate; capacity; idle reclaim | 45-min cap; CPU quota | uptime | non-starter |

---

## Ranking for Atlas MVP @ ₹0 [RECOMMENDATION]

1. **GitHub Actions public-repo runners** — unlimited free compute bigger than the paid VM we spec'd (4c/16 GB > 2c/4 GB), Docker-native so `DockerExecutor` ships unchanged, per-job ephemeral isolation, trigger path fully documented. Accept and manage the ToS-gray-area + public-logs caveats consciously.
2. **Oracle Always-Free** — best *always-on* $0 option if and only if you have a card and patience for capacity/reclaim games. Keep as the "graduate to always-on" step when volume grows.
3. **Vercel Sandbox Hobby** — cleanest security model and reuses your existing Vercel account, but needs a new executor and the 45-min/CPU-quota envelope is tightest.
4. **Home PC** — do this *this week* regardless: it validates the entire prod loop end-to-end before any remote choice matters.
5. ~~Render~~ — ruled out with evidence.

### Suggested sequence (all ₹0)

```text
Week 1: Phase-0 local items (Dockerfile, CI authoring, reaper)  [AGENT]
        + home-PC shadow execution against dev DB               [YOU+AGENT]
Week 2: Supabase migration (you approve/apply)                  [HUMAN]
        + benchmark-image workflow merged → GHCR                [HUMAN merge]
Week 3: Add benchmark-execute.yml dispatch workflow             [AGENT]
        + PAT + Actions secrets                                 [HUMAN]
        → first real remote ₹0 execution
Later:  if volume outgrows Actions → OCI A1 VM (card permitting)
        or paid VM (~€4/mo) — Executor interface makes this a config flip.
```

---

## Decisions Requested

1. Adopt **GitHub Actions as the MVP execution plane** (accepting documented caveats)?
2. Comfortable with benchmark prompts/logs being **public** on this repo? If not, private-repo fallback = 2,000 min/month ≈ 30–60 executions — still ₹0 but rationed.
3. Proceed with Week-1 Phase-0 items now (local-only, no push)?
