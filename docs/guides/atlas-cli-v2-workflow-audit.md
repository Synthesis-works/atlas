# Atlas CLI v2 — Agent Workflow Audit

> **Status:** Input document only. **No v2 features were implemented.**
> **Branch:** `feature/atlas-cli-v2` (created from frozen v1 `0b99d6b`)
> **CLI under test:** `atlas-cli 0.1.0` (v1, installed console script, editable)
> **Date:** 2026-08-29
> **Backend:** healthy at `http://localhost:8000`, seeded `atlas_dev.db` (data preserved; no re-seed)

## 1. The question

> **If an AI agent had Atlas CLI and nothing else, could it actually operate Atlas effectively?**

This audit drives **only the CLI** (installed `atlas` console script) to exercise real Atlas
workflows. No Python scripts, no direct HTTP to the API, no backend internals for the workflow
itself. The only glue used outside the CLI is PowerShell `ConvertFrom-Json` for parsing CLI stdout
(which is exactly what an agent would do). This documents where v1 is genuinely agent-usable and
where it breaks down, so v2 can be designed from evidence rather than from the earlier speculative
feature list.

## 2. Method

Every task below was run live and reproduces with the exact commands shown. Exit codes were checked
after every invocation. A single real execution was submitted during the audit (documented in §6) —
the only state change; everything else is read-only.

## 3. Where v1 is genuinely useful for an agent (verified strengths)

| Strength | Evidence (observed) |
|---|---|
| Health check without auth | `atlas --output json health` → clean JSON, exit 0. Also usable as a readiness probe (`overall` + exit 1 when degraded). |
| Authentication is scriptable | `'password' \| atlas login --email … --password-stdin` → non-interactive, exit 0, persists token; `ATLAS_TOKEN` env var overrides for CI. `logout` works offline and is idempotent. |
| Full-UUID JSON on stdout | Every `--output json` command printed one document to stdout with full UUIDs (unlike human tables, which abbreviate IDs to 8 chars). |
| Predictable exit codes | Verified live: 0 success, 2 usage (bad choice, unknown command, mutually exclusive flags), 3 no-token, 4 forbidden, 5 not-found, 7 malformed UUID, 130 Ctrl-C; JSON error envelope `{"error":{status,code,message}}` on **stderr** with clean stdout. |
| Command chaining works | Discover version id via `leaderboard model mock --history` JSON → feed into `leaderboard benchmark <vid>` in one PowerShell line. |
| Concise modes | `--quiet` prints nothing (exit-status-only checks); human mode is compact for humans. |
| Global `--timeout` | Fine-grained per-request timeout exists as a first-class global option. |
| Read-heavy coverage | dashboard, activity, leaderboard (model summary/history/benchmarks + benchmark leaderboard), run list/get, report list/get/export all worked against seeded data. |

## 4. Representative tasks — live results

| Task | Commands used | Outcome |
|---|---|---|
| Health/health auth | `atlas --output json health` → login → `atlas whoami` | exit 0/0/0. Health needs no token. Details are clean (`api`, `liveness`, `readiness`, `overall`). |
| Discover benchmarks | `atlas --output json benchmark list` | 8 published benchmarks, full IDs + names, exit 0. |
| Inspect a benchmark | `atlas benchmark get <id>` / `atlas benchmark versions <id>` | exit **4** for all seeded published benchmarks (org-membership 403). The seeded published benchmarks belong to an org the demo user is not a member of. Blocked. |
| Inspect benchmark version | `atlas leaderboard benchmark <version-id>` (real version id) | exit 0, ranked entries returned. |
| List runs | `atlas --output json run list --limit 3` | 115 total; full UUIDs, status, model, timestamps. exit 0. |
| Inspect a run | `atlas run get <execution-id>` | exit 0 with full detail (but see §5/P3 — status surfaces are incoherent). |
| Watch a run | `atlas run watch <id> --interval 2` | **No `--timeout` option.** On a stuck run it polls indefinitely (see §6). Only Ctrl-C (exit 130) stops it. |
| Submit a run | `atlas run submit <version-id> --target-model mock` | exit 0, QUEUED → RUNNING. (Note: default target is `gemini-2.5-flash` — a paid provider — beware cost.) |
| Inspect a report | `atlas --output json report get <run-id>` | exit 0, score/details (when report exists). |
| Export a report | `atlas report export <run-id> --output-file <path>`; `--format csv` | exit 0 both; JSON 1884 bytes, CSV 647 bytes. Raw `-` to stdout works (bytes, not JSON). |
| Leaderboard/model | `atlas leaderboard model mock [--history\|--benchmarks]`; `leaderboard benchmark <vid>` | exit 0 all; `--history` exposes the only usable path to **benchmark version IDs**. |
| Dashboard/activity | `atlas dashboard`; `atlas activity --type executions|benchmarks|models --limit N` | exit 0 all. `activity --type benchmarks` doubles as a benchmark-ID catalog without org membership. |

## 5. Pain points (severity-ranked)

**P1 — Run status is incoherent across endpoints/CLI surfaces (critical).**
One run (`bf6c70b3`), four different statuses from four CLI commands:

| Surface | Command | Reported status |
|---|---|---|
| Execution endpoint | `run get` / `run list` / `run watch` | `RUNNING`, `started_at=null`, 0/1 items |
| Report row | `report list` / `report get` | `evaluation_status: COMPLETED`, `overall_score: null` |
| Export payload | `report export` (JSON body) | embedded `execution.status: COMPLETED`, `report: null` |
| Dashboard | `atlas --output json dashboard` | `active_executions`: `status: Completed`, `progress: 100` |

An agent cannot trust any single surface to decide "is my run done". The CLI faithfully renders
four disagreeing backends (executions, reports, export, dashboard). This is the single biggest
obstacle to autonomous operation: a loop like *submit → watch → export* needs one authoritative
terminal-state signal. (Pre-existing backend data-source discrepancy — see the manual-testing guide
§10.4 — now elevated from "quirk" to "agent blocker".)

**P2 — There is no CLI path to benchmark version IDs for arbitrary benchmarks (critical blocker).**
`benchmark list` returns benchmark IDs only. `benchmark versions`/`benchmark get` → 403 for every
seed-published benchmark (org membership). The *only* working discovery is
`leaderboard model <name> --history`, and only for models that already have runs. Therefore an agent
cannot, in the general case, find a version ID it needs to `run submit`. The run-entry workflow is
gated by stale/absent org membership, not by capability.

**P3 — `run watch` cannot be time-bounded (high).** No `--timeout`/`--max-iterations`; on stuck or
slow runs it hangs forever, wasting the agent's session. Needs a bound plus a non-zero terminal
state (e.g. `TIMEOUT`).

**P4 — `run submit` has a costly default (high).** Default `--target-model gemini-2.5-flash`
(falls through to a real provider adapter). An agent that submits "innocently" from a benchmark ID
it found in `activity` hits a real external API. Needs explicit `--yes`/dry-run/preflight or a
non-paying default.

**P5 — Human output abbreviates IDs (medium).** Tables show 8-char id prefixes. Harmless for humans,
but it punishes mixed-mode agent output and teaches the wrong pattern; agents must re-run with
`--output json` to get usable IDs.

**P6 — Login is interactive by default (medium).** Without `--password-stdin` + `--email`,
`atlas login` prompts and an unattended agent hangs. The non-interactive path exists but must be
discovered in help; a `--no-interactive`-style guard or CI env story would harden it.

**P7 — No built-in retry/backoff for transient failures (medium).** Errors are surfaced cleanly
(exit codes + envelope) but the agent must implement retry itself. A shared `--retries`/`--retry-delay`
couple would be idiomatic for agent loops.

**P8 — JSON payload sizes are uneven (low/medium).** `dashboard --output json` is by far the largest
(full nested object with running_jobs, active_executions, activity, capability…). Fine in human
reviews; heavy for agent context-window economics. Lighter focused endpoints (activity/run/report)
are well-formed. A `--fields` selector or stable projections would help agents on large dashboards.

**P9 — Heterogeneous activity schemas (low).** `activity --type` returns three different item shapes
(`name`/`state` for benchmarks; `id`/`benchmark_name`/`target_model`/`status` for executions;
`name`/`last_executed_at`/`execution_count` for models). Correct but requires per-type parsing
knowledge. A documented schema or `--json-schema` self-description would remove guesswork.

**P10 — Observable discovery of endpoint mappings (low).** Fields like `benchmark_version` (in
`leaderboard model --history`) vs `benchmark_version_id` (in `run list`) differ across endpoints;
agents must learn each shape empirically (this audit's notes, or the guide). Naming uniformity is a
cheap, high-value cleanup.

## 6. Notable live observation (documented state change)

A real run was submitted to exercise the full lifecycle: `run submit 181d1c91-… --target-model mock`
→ execution `bf6c70b3-0f23-451d-9c1d-1e84f41bb63d`. It reached `RUNNING` (eager worker), then:
`run watch` polled without progress; `report list` showed a `COMPLETED` report row; the execution
endpoint kept `RUNNING`. This environment's execution-completion pipeline does not drive executions
to a terminal state, so the watch-and-export loop stalls even on a "successful" run. This is the
concrete manifestation of P1 and P3. (The submission and its report row remain in the DB as an audit
artifact.)

## 7. Gaps mapped to the agent concerns requested

| Agent concern | Verdict | Evidence |
|---|---|---|
| Machine-readable output | **Good** — `--output json` everywhere, one doc on stdout, full IDs | §3 |
| Predictable exit codes | **Good** — 0/2/3/4/5/7/130 verified; JSON error envelope on stderr | §3, §4 |
| Discovering IDs | **Poor** — version IDs unreachable for arbitrary benchmarks (P2); IDs discoverable only via leaderboard history; human mode abbreviates (P5) | P2, P5 |
| Chaining commands | **Good** — stdout JSON chains cleanly (sorted lists, pagination keys documented) | §3, §4 |
| Avoiding interactive prompts | **Partial** — `--password-stdin` works; default `login` prompts (P6) | P6 |
| Concise output | **Good/Partial** — `--quiet` and tight tables ✓; dashboard JSON heavy (P8) | P8 |
| Authentication | **Good** — login/logout + `ATLAS_TOKEN` + profiles + `--base-url`; no PAT flow (known v1 scope) | §3 |
| Errors/retries | **Partial** — errors excellent; retries absent (P7) | P7 |
| Commands an agent would naturally want | **Partial** — missing: time-bounded watch; authoritative run-completion signal; version-ID discovery; `run submit` preflight/dry-run; model catalog/search; schema self-description | P1, P2, P3, P4, P9 |

## 8. Recommended v2 design directions (input only — NOT built)

These follow directly from the evidence above and supersede/augment the earlier speculative v2 list:

1. **Authoritative run life-cycle primitive.** One command (or one field) that resolves the cross-surface
   status conflict (P1) and blocks until a single terminal state with a bound (P3), e.g.
   `run wait <id> --timeout N --interval S → terminal status` on exit 0 and `TIMEOUT` on exit X.
2. **Version-ID discovery surface.** A first-class, membership-agnostic listing of benchmark versions
   (e.g. extend `benchmark list`/`benchmark versions` to return published versions with IDs), fixing P2.
3. **Cost-safe submit ergonomics.** `run submit --preview` (resolved target/version/cost estimate) and/or
   an explicit-target guard so paying targets are opt-in (P4).
4. **Agent ergonomics pass:** `--retries`/`--retry-delay` (P7), ID-friendly human tables or documented
   truncation (P5), `--json-schema`/shared naming (P9/P10), `--fields` for heavy payloads (P8), and a
   `--no-interactive` guard for login/prompts (P6).
5. **Keep what works.** Exit codes, JSON-on-stdout/errors-on-stderr contract, `--quiet`, global options,
   chaining — do not regress these in v2.

## 9. Verdict

**Partial.** Atlas CLI v1 is a sound, predictable, scriptable interface for reading Atlas and for
authentication — an agent can absolutely use it for health, discovery of published benchmarks,
activity, leaderboards, runs, and reports, and (with care) submitting runs. But it is **not yet**
operable end-to-end by an agent with "nothing else": the run-status incoherence (P1) and the
unreachable benchmark-version IDs (P2) break the acquisition→verify→submit→wait→consume loop, and
`watch` has no bound (P3). Closing those three — plus making paid submits explicit (P4) — is the
difference between "an agent can drive Atlas" and "an agent can *operate* Atlas".

## Appendix — audit artifacts

- Commands executed: everything in §4 (all printed with `--output json` where applicable; exit codes
  captured after each). Raw outputs captured to live stdout during the session.
- Created during audit: execution `bf6c70b3-0f23-451d-9c1d-1e84f41bb63d` + its report row
  (`evaluation_status COMPLETED`, score null), plus temp exports (`audit-export.json` 1884 B,
  `audit-export.csv` 647 B) under the OS temp dir.
- No source code changed; branch `feature/atlas-cli-v2` contains no code diffs vs v1 at commit time.