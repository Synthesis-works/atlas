# Repository Audit — Project Atlas

**Date:** 2026-07-13
**Branch:** `audit/repo-review`
**Scope:** Structure, documentation, dependencies, testing, CI/CD, code quality, git hygiene

This audit is based on a full file tree scan, README review, dependency file review, and CI config review. Findings are organized by category with severity ratings: **Critical** (blocks reliable collaboration/production use), **Important** (should be fixed soon), **Nice-to-have** (polish).

---

## 1. Project Structure & Organization

**Present:**
- Clear monorepo layout following a stated "Atlas V1 Repository Architecture" (documented in README): `apps/`, `services/`, `packages/`, `benchmarks/`, `datasets/`, `infrastructure/`, `docker/`, `scripts/`, `docs/`, `tests/`, `configs/`, `sdk/`, `cli/`.
- Real, non-trivial code exists in `packages/` — notably `packages/database`, `packages/benchmark`, `packages/llm`, `packages/orchestrator`, `packages/runtime`, `packages/evaluation`, `packages/research`.

**Missing / Broken:**
- **[Important]** The large majority of top-level folders are empty scaffolding (only `.gitkeep` present): `apps/admin`, `apps/web`, `sdk/python`, `sdk/typescript`, `cli/commands`, `cli/templates`, `infrastructure/*`, most of `docker/*`, most of `services/*`, most of `configs/*`. This makes it hard to tell what's actually implemented vs. planned from the tree alone — consider a `docs/roadmap` note or README section marking what's live vs. stubbed.
- **[Important]** Duplicate/near-identical empty service folders: `services/auth-service` **and** `services/auth`; `services/evaluation-service` **and** `services/evaluation`; but only `services/execution-service` (no plain `execution`). This inconsistency should be resolved before real service code is added, or it will be unclear which folder is canonical.
- **[Nice-to-have]** Two parallel config directories: `config/` (singular, contains a real file `providers.json`) and `configs/` (plural, contains only empty `development/production/staging/testing` folders). Consider consolidating into one convention.
- **[Nice-to-have]** `docs/atlas-bible/` exists but is empty — if this is meant to hold core project specs/philosophy, it's currently just a placeholder with no content.

---

## 2. Documentation

**Present:**
- `README.md` explains the project purpose, repo structure, and has a "Quick Start" for running benchmark experiments (`scripts/run_experiment.py`), resuming experiments, generating reports, and validating providers.
- `LICENSE` file present.
- `.github/PULL_REQUEST_TEMPLATE.md` exists.
- `docs/BENCHMARKS.md`, `docs/RESEARCH_GUIDE.md`, `docs/adr/ADR-Database-Architecture.md`, `docs/database_naming_conventions.md`, `docs/postgres_backup_restore.md` — decent architecture/process documentation exists for the parts that are built.

**Missing / Broken:**
- **[Critical]** README references `scripts/mcnemar_test.py` in the "Compare Prompts (McNemar's Test)" section, but this script does not exist in the repo. Only `packages/research/statistics/mcnemar.py` (the underlying logic, no CLI entry point) is present. This is a documented-but-nonexistent feature — either build the script or fix the README.
- **[Important]** README's PowerShell code blocks use double backticks (`` ``powershell ``) instead of triple backticks (` ```powershell `). This will render broken/unstyled on GitHub — all four PowerShell examples are affected.
- **[Important]** No `CONTRIBUTING.md` — for a multi-contributor project with a PR template already in place, there's no guidance on branch naming, commit conventions, or review process.
- **[Nice-to-have]** No `CODE_OF_CONDUCT.md`.
- **[Nice-to-have]** `.github/ISSUE_TEMPLATE/` exists as a folder but contains no actual templates (only `.gitkeep`).

---

## 3. Dependency Management

**Present:**
- Root `requirements.txt` with three pinned-minimum packages: `pydantic>=2.0.0`, `PyYAML>=6.0`, `httpx>=0.24.0`.
- `packages/database/pyproject.toml` — a separate, package-scoped dependency manifest.
- `.env.example` present at root (good practice for documenting required environment variables).

**Missing / Broken:**
- **[Critical]** `requirements.txt` is drastically incomplete relative to the actual codebase. Code under `packages/database` uses Alembic (`alembic.ini`, `alembic/env.py`) and almost certainly SQLAlchemy, neither of which is listed. `packages/llm/clients/` has dedicated clients for Gemini, Grok, Mistral, and Ollama — none of the corresponding SDKs appear in `requirements.txt`. Anyone doing a fresh `pip install -r requirements.txt` will hit import errors immediately.
- **[Critical]** No lockfile anywhere (no `poetry.lock`, no `requirements-lock.txt`, no `pip-compile` output). Combined with two separate dependency manifests (root `requirements.txt` vs. `packages/database/pyproject.toml`), builds are not reproducible. This is the core gap your upcoming Docker + Poetry integration task should resolve — consolidate to a single Poetry-managed dependency source with a committed lockfile.
- **[Important]** No `pytest` (or any test runner) listed in dependencies despite test files existing (`tests/benchmark/test_foundation.py`, `packages/database/tests/*`).

---

## 4. Testing

**Present:**
- `tests/benchmark/test_foundation.py` — one real test file at the top level.
- `packages/database/tests/` — three real files: `conftest.py`, `test_base_repository.py`, `test_models.py`.

**Missing / Broken:**
- **[Critical]** Nearly the entire `tests/` tree is empty scaffolding: `tests/backend/`, `tests/evaluation/`, `tests/frontend/`, `tests/integration/`, `tests/performance/` all contain only `.gitkeep`. Given the size and complexity of `packages/orchestrator` (8-stage pipeline), `packages/evaluation` (extractors, judges, metrics, normalizers), `packages/llm` (4 provider clients), and `packages/runtime` (sandboxing, security, execution) — this represents effectively **zero test coverage** on the core evaluation and execution logic. Bugs in sandboxing/security code (`packages/runtime/security/`) are especially risky to ship untested.
- **[Important]** No test coverage tooling configured (no `pytest.ini`, `.coveragerc`, or coverage config visible) to even measure the gap.

---

## 5. CI/CD

**Present:**
- `.github/workflows/` directory exists.

**Missing / Broken:**
- **[Critical]** The workflows directory contains only a `.gitkeep` — there is **no CI configured at all**. No automated test runs, no linting, no build checks on pull requests. Given three branches (this audit, the benchmark PR, and the Docker/Poetry PR) are about to be opened against `main`, there is currently nothing automatically verifying they don't break the build.
- Recommendation: even a minimal workflow (install deps, run `pytest`, run a linter) on `pull_request` would meaningfully de-risk future merges.

---

## 6. Code Quality

**Present:**
- Codebase in `packages/` shows a deliberate layered architecture (interfaces/, models/, validation/, registry/ pattern repeated across `benchmark`, `runtime`, `evaluation` — suggests consistent internal conventions).
- `Makefile` present at root, suggesting some standardized task automation exists (contents not reviewed in this pass — worth a follow-up check that it references real, working commands).

**Missing / Broken:**
- **[Important]** No linter or formatter configuration found at the root (no `ruff.toml`, `.flake8`, `pyproject.toml` with `[tool.black]`/`[tool.ruff]`, or `.pre-commit-config.yaml`). Without this, style consistency across contributors isn't enforced.
- **[Nice-to-have]** No `.dockerignore` found alongside `docker-compose.yml` — worth adding once Docker work (Task 3) begins, to avoid bloating build contexts.

---

## 7. Git & Repository Hygiene

**Present:**
- `.gitignore` present at root.
- `.env.example` correctly separated from a real `.env` (which is presumably gitignored — worth double-checking `.gitignore` explicitly excludes `.env`).

**Missing / Broken:**
- **[Important]** `results/2026-07-08/.../response.json` and `eval_result.json` — actual experiment run outputs — are committed directly into the repository under `results/`. These are regenerable artifacts from running benchmarks locally; committing them will bloat repo history over time as more experiments run. Recommend gitignoring `results/` (or a dated subpattern of it) and treating it as local/artifact storage instead, unless there's a deliberate reason to version historical results.
- **[Nice-to-have]** `datasets/humaneval/HumanEval.jsonl` and `datasets/mbpp/mbpp.jsonl` are committed directly. `datasets/licenses/` exists (presumably to track dataset licensing/attribution) but is empty — worth populating this before distributing the repo more widely, since HumanEval/MBPP typically carry their own usage terms.

---

## Summary — Priority Action Items

| Priority | Item |
|---|---|
| Critical | Fix `requirements.txt` to include all actual runtime dependencies (SQLAlchemy, Alembic, provider SDKs, pytest) |
| Critical | Consolidate dependency management to one source (Poetry) with a committed lockfile — feeds directly into the Docker/Poetry task |
| Critical | Add CI workflow(s) that at minimum install deps and run tests on PR |
| Critical | Add real tests for `orchestrator`, `evaluation`, `llm`, `runtime` — currently near-zero coverage on core logic |
| Critical | Fix or build `scripts/mcnemar_test.py` to match README, or update README |
| Important | Resolve duplicate service folders (`auth` vs `auth-service`, `evaluation` vs `evaluation-service`) |
| Important | Fix broken PowerShell code fences in README (double backtick → triple backtick) |
| Important | Add `CONTRIBUTING.md` given multiple contributors and an existing PR template |
| Important | Add linter/formatter config (ruff/black + pre-commit) |
| Important | Move `results/` run outputs out of version control |
