# Atlas CLI — Release & Distribution Guide

- **Date:** 2026-09-05
- **Branch:** `feature/atlas-cli-v3`
- **Applies to:** `atlas-cli` 0.1.0 (`D:\atlas\cli`) + `atlas-sdk` 0.1.0 (`D:\atlas\sdk\python`)
- **Landscape:** the CLI bundles the SDK and `packages/llm` into one self-contained
  distribution. Wheel and sdist are built through a release-time staging step and
  validated offline in fresh virtualenvs; publishing to PyPI is **not yet enabled**.

---

## 1. Why a staging build?

`cli/pyproject.toml` points `package-dir` at sibling trees in the monorepo:

```toml
[tool.setuptools.package-dir]
cli = "cli"
atlas_sdk = "../sdk/python/atlas_sdk"
packages = "../packages"
```

That resolves correctly for **direct wheel builds** and for **editable installs**.
It does **not** survive the source-distribution step: when setuptools re-roots the
project into `atlas_cli-0.1.0/` inside the sdist, the `../sdk/...` references now
escape the sdist and the sdist is not self-contained — copying to
`atlas_cli-0.1.0/../sdk/...` produces a broken archive that cannot rebuild into a
wheel.

Release artifacts are therefore produced from a **temporary self-contained staging
tree**:

| Staged path | Copied from |
|---|---|
| `stage/cli` | `cli/cli` |
| `stage/atlas_sdk` | `sdk/python/atlas_sdk` |
| `stage/packages` | `packages/__init__.py` + `packages/llm` |
| `stage/README.md` | `cli/README.md` |

The staged `pyproject.toml` is the real `cli/pyproject.toml` with `package-dir`
rewritten to `cli = "cli"`, `atlas_sdk = "atlas_sdk"`, `packages = "packages"`.
Everything else (dependencies, entry point, license, readme) is inherited directly.
No source copies live in the repository — the staging tree is created under the
system temp dir and removed on exit.

## 2. Build and validate

```bash
pip install -e ./sdk/python -e ./cli        # dev / editable workflow (unchanged)
uv build --wheel ./cli                       # quick wheel-only check (no staging)
python scripts/build_cli_dist.py             # staged wheel + sdist -> cli/dist/
python scripts/validate_cli_dist.py          # offline validation (fresh venvs)
```

`scripts/build_cli_dist.py`:

- copies the three package trees + README into a fresh temp staging dir,
- rewrites `package-dir` to staged (self-contained) paths,
- runs `uv build` for both wheel and sdist into `--out-dir` (default `cli/dist/`),
- guarantees the sdist is self-contained and installable outside the checkout.

`scripts/validate_cli_dist.py` validates each artifact **without** a live backend or
provider key:

- installs the artifact into a fresh virtualenv **created outside the repository**,
- asserts `cli`, `atlas_sdk`, `packages.llm` (incl. the provider client modules)
  import cleanly,
- asserts `atlas --help` exits 0 and `atlas --version` equals the package version,
- asserts wheel/sdist metadata declares `Version` / `License-Expression: MIT` and
  **no** `atlas-sdk` / `atlas-llm` `Requires-Dist`,
- asserts `atlas agent` without credentials **fails gracefully with exit code 10**
  (“Atlas agent brain unavailable…”), proving the provider chain loads without an
  import-time crash.

## 3. Versioning (single source)

The version lives in exactly one place — `cli/cli/__init__.py`:

```python
__version__ = "0.1.0"
```

`cli/pyproject.toml` declares `dynamic = ["version"]` and derives it via:

```toml
[tool.setuptools.dynamic]
version = {attr = "cli.__version__"}
```

`atlas --version` (`cli.app`) reads the same `cli.__version__`. Therefore the
installed package, wheel metadata, sdist metadata, and `atlas --version` all agree
by construction; bump the version in one file only.

## 4. CI

`.github/workflows/cli.yml` runs on PRs touching `cli/**`, `sdk/python/**`,
`packages/llm/**`, the build/validate scripts, or the workflow itself, and on pushes
to `main` / `feature/**`.

- `test` job: editable install, `ruff check` over the CLI/SDK/LLM surface,
  `ruff format --check` and `mypy` **only on the files changed by the PR**
  (the full directories have pre-existing mypy/format drift unrelated to this work),
  SDK + CLI pytest suites.
- `build` job: staged wheel + sdist via uv, offline validation, artifact upload.

## 5. Publishing: renamed distribution, trusted publishing wired

> **Distribution-name decision (2026-09-07):** the distribution on PyPI is
> **`synthesis-atlas-cli`** — the executable stays **`atlas`**. The originally
> intended `atlas-cli` name was permanently blocked by PyPI's similarity rule
> (existing `atlascli` project, verified with Warehouse's own check via
> `canipypi`); `synthesis-atlas-cli` passed the same check and was registered.

The distribution name lives in exactly one metadata location —
`cli/pyproject.toml` (`name = "synthesis-atlas-cli"`). It is independent of:

- the installed executable (`[project.scripts] atlas = "cli.app:entrypoint"`),
- the runtime dependencies (`click`, `httpx`, `pydantic[email]`),
- `build_cli_dist.py` / `validate_cli_dist.py`, which assert on the embedded
  version + `atlas` executable only, not on the distribution name,
- the GitHub Actions `publish-atlas-cli.yml` workflow (uploads
  `dist/artifacts/*` generically), whose only name-dependent convention is the
  human-facing release tag `synthesis-atlas-cli-v*`.

Status:

- PyPI project **`synthesis-atlas-cli`**: registered with a **pending trusted
  publisher** (OIDC) for this repository's `publish-atlas-cli.yml` workflow and
  the `pypi-publish` environment. `GET https://pypi.org/pypi/synthesis-atlas-cli/json`
  returns 404 until the first release is published.
- GitHub Environment **`pypi-publish`**: exists in repo Settings (protect it
  with required reviewers).
- The wheel/sdist are fully self-contained: a clean-environment install from the
  built artifacts pulls only `click`, `httpx`, `pydantic` from PyPI and imports
  `cli`, `atlas_sdk`, and `packages.llm` inline (verified in a fresh venv outside
  the repository). Search-free note: the PyPI `atlas-sdk` name belongs to an
  unrelated project (`atlassistant/atlas-sdk`), which is why the SDK is bundled
  rather than depended on.

The workflow only runs for an explicit tag push `synthesis-atlas-cli-v*` **and**
an explicit `github.ref_type == 'tag'` condition, on the `pypi-publish` GitHub
Environment. It uses OIDC trusted publishing (`pypa/gh-action-pypi-publish` with
`id-token: write`), so no long-lived token is stored in repository secrets, and
`skip-existing` makes re-releases idempotent.

Until the release tag is pushed, ordinary CI (PRs, branch pushes, main pushes)
can never invoke the publish job: it has no trigger path and the upload fails
closed if it somehow runs.

### Release steps

To publish the first release:

1. Confirm the tag you push matches the distribution + version: for
   `__version__ = "0.1.0"` the release tag is **`synthesis-atlas-cli-v0.1.0`**.
2. Push the tag from a merged `main` (the workflow builds from the tagged source,
   validates wheel + sdist in fresh venvs, and uploads via trusted publishing —
   the pending publisher becomes the real one on first upload).
3. Verify at pypi.org/project/synthesis-atlas-cli/, then `python -m pip install
   synthesis-atlas-cli` in an empty venv and run `atlas --version`.

## 6. Definition of done for a release

- [ ] Version bumped in `cli/cli/__init__.py` (single source).
- [ ] `python scripts/build_cli_dist.py` produces matching wheel + sdist.
- [ ] `python scripts/validate_cli_dist.py` passes for both artifacts.
- [ ] CI `atlas-cli CI` workflow is green on the release branch.
- [ ] Tag `synthesis-atlas-cli-vX.Y.Z` pushed **after** the branch is merged.