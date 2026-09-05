"""Release-time staging build for the atlas-cli distribution.

The CLI's monorepo pyproject (``cli/pyproject.toml``) packages sibling trees
(``sdk/python/atlas_sdk`` and ``packages``) through relative ``package-dir``
paths. That resolves for direct wheel builds but breaks the sdist: when
setuptools re-roots the project inside an sdist, the ``../`` references no
longer exist, so the sdist must be self-contained.

This script stages a temporary, self-contained project tree (the three package
trees plus a rewritten pyproject whose ``package-dir`` points at the staged
dirs), builds wheel + sdist with ``uv build``, and emits them into an output
directory. No source copies ever live in the repository; the staging tree is
created under the system temp dir and removed on exit.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_DIR = REPO_ROOT / "cli"
SDK_SRC = REPO_ROOT / "sdk" / "python" / "atlas_sdk"
PACKAGES_INIT = REPO_ROOT / "packages" / "__init__.py"
PACKAGES_LLM = REPO_ROOT / "packages" / "llm"

COPY_TREES: list[tuple[Path, str]] = [
    (CLI_DIR / "cli", "cli"),
    (SDK_SRC, "atlas_sdk"),
    (PACKAGES_LLM, "packages/llm"),
]

STAGED_PACKAGE_DIR = {
    "cli": "cli",
    "atlas_sdk": "atlas_sdk",
    "packages": "packages",
}


def stage_project(stage: Path) -> None:
    """Copy the three package trees plus README into ``stage``."""
    for src, rel in COPY_TREES:
        shutil.copytree(src, stage / rel)
    shutil.copy2(CLI_DIR / "README.md", stage / "README.md")
    shutil.copy2(PACKAGES_INIT, stage / "packages" / "__init__.py")
    (stage / "cli").mkdir(parents=True, exist_ok=True)
    (stage / "atlas_sdk").mkdir(parents=True, exist_ok=True)
    (stage / "packages").mkdir(parents=True, exist_ok=True)


def rewrite_pyproject(stage: Path) -> None:
    """Rewrite the cli pyproject so ``package-dir`` points at staged dirs."""
    project_toml = CLI_DIR / "pyproject.toml"
    with project_toml.open("rb") as fh:
        cfg = tomllib.load(fh)
    if cfg["tool"]["setuptools"].get("package-dir") != {
        "cli": "cli",
        "atlas_sdk": "../sdk/python/atlas_sdk",
        "packages": "../packages",
    }:
        raise SystemExit("unexpected [tool.setuptools.package-dir] in cli/pyproject.toml")
    text = project_toml.read_text(encoding="utf-8")
    old = 'atlas_sdk = "../sdk/python/atlas_sdk"\npackages = "../packages"'
    new = 'atlas_sdk = "atlas_sdk"\npackages = "packages"'
    if old not in text:
        raise SystemExit("package-dir block not found in cli/pyproject.toml")
    (stage / "pyproject.toml").write_text(text.replace(old, new), encoding="utf-8")


def build(stage: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["uv", "build", str(stage), "--out-dir", str(out_dir)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=CLI_DIR / "dist",
        help="Directory for the built artifacts (default: cli/dist).",
    )
    parser.add_argument(
        "--stage-dir",
        type=Path,
        default=None,
        help="Use this staging dir instead of a system temp dir (kept on exit).",
    )
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()

    if args.stage_dir is not None:
        stage_dir = args.stage_dir.resolve()
        stage_dir.mkdir(parents=True, exist_ok=True)
        keep = True
    else:
        stage_dir = Path(tempfile.mkdtemp(prefix="atlas-cli-stage-"))
        keep = False

    try:
        stage_project(stage_dir)
        rewrite_pyproject(stage_dir)
        build(stage_dir, out_dir)
    finally:
        if not keep:
            shutil.rmtree(stage_dir, ignore_errors=True)

    print(f"Built artifacts in: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
