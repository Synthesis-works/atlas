"""Offline validation of built atlas-cli distribution artifacts.

Verifies the wheel and the sdist without any live backend or provider key:

* fresh virtualenv created outside the repository, artifact installed via pip,
* ``cli`` / ``atlas_sdk`` / ``packages.llm`` import cleanly,
* ``atlas --help`` exits 0 and ``atlas --version`` matches the package source,
* the wheel/sdist metadata declares no ``atlas-sdk``/``atlas-llm`` dependency,
* running ``atlas agent`` without credentials fails gracefully (exit 10) —
  proving the provider chain loads without an import-time crash.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI_PKG_INIT = REPO_ROOT / "cli" / "cli" / "__init__.py"

NO_KEY_RUN = ("agent", "hello")
NO_KEY_EXPECTED = ("Atlas agent brain unavailable", "GROQ_API_KEY", "GEMINI_API_KEY")


def find_version() -> str:
    m = re.search(r'__version__\s*=\s*"([^"]+)"', CLI_PKG_INIT.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("cannot parse __version__ from cli/cli/__init__.py")
    return m.group(1)


def check_metadata(path: Path, *, is_wheel: bool, expected: str) -> None:
    if is_wheel:
        with zipfile.ZipFile(path) as zf:
            meta_name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
            meta = zf.read(meta_name).decode("utf-8")
            names = zf.namelist()
    else:
        with tarfile.open(path) as tf:
            meta_name = next(n for n in tf.getnames() if n.endswith("PKG-INFO"))
            meta_fh = tf.extractfile(meta_name)
            assert meta_fh is not None, "PKG-INFO missing from sdist"
            meta = meta_fh.read().decode("utf-8")
            names = tf.getnames()
    lines = [l for l in meta.splitlines() if l.startswith("Requires-Dist:")]
    assert not any("atlas-sdk" in l or "atlas-llm" in l for l in lines), lines
    assert f"Version: {expected}" in meta, "metadata version mismatch"
    assert "License-Expression: MIT" in meta, "metadata license mismatch"
    if is_wheel:
        for pkg in ("atlas_sdk/", "cli/", "packages/llm/"):
            assert any(pkg in n for n in names), f"{pkg} missing from {path.name}"


def make_venv() -> tuple[Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="atlas-cli-validate-"))
    venv.EnvBuilder(with_pip=True).create(tmp)
    py = tmp / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    atlas = tmp / ("Scripts/atlas.exe" if os.name == "nt" else "bin/atlas")
    return py, atlas


def install(py: Path, artifact: Path) -> None:
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "--quiet", str(artifact)], check=True)


def run_checks(py: Path, atlas: Path, expected: str, *, agent_graceful: bool = False) -> None:
    code = (
        "import cli, atlas_sdk, packages.llm; "
        "from packages.llm import ProviderAdapter, Prompt; "
        "import packages.llm.clients.gemini, packages.llm.clients.grok, "
        "packages.llm.clients.groq, packages.llm.clients.ollama, packages.llm.registry"
    )
    subprocess.run([str(py), "-c", code], check=True)
    res = subprocess.run([str(atlas), "--help"], capture_output=True, text=True)
    assert res.returncode == 0, (res.returncode, res.stderr)
    res = subprocess.run([str(atlas), "--version"], capture_output=True, text=True)
    assert res.returncode == 0 and expected in res.stdout, (res.returncode, res.stdout, res.stderr)
    if agent_graceful:
        res = subprocess.run([str(atlas), *NO_KEY_RUN], capture_output=True, text=True)
        assert res.returncode == 10, (res.returncode, res.stderr)
        assert any(k in (res.stdout + res.stderr) for k in NO_KEY_EXPECTED), res.stdout + res.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=REPO_ROOT / "cli" / "dist")
    args = parser.parse_args()
    dist = args.dist_dir.resolve()
    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(p for p in dist.glob("*.tar.gz") if p.stat().st_size > 1000)
    if not wheels or not sdists:
        raise SystemExit(f"need exactly one wheel and one sdist in {dist}: {wheels} {sdists}")
    expected = find_version()

    py, atlas = make_venv()
    try:
        install(py, wheels[0])
        check_metadata(wheels[0], is_wheel=True, expected=expected)
        run_checks(py, atlas, expected)
        print(f"[ok] wheel {wheels[0].name} (v{expected})")
    finally:
        shutil_rmtree(py.parent)

    py, atlas = make_venv()
    try:
        install(py, sdists[0])
        check_metadata(sdists[0], is_wheel=False, expected=expected)
        run_checks(py, atlas, expected, agent_graceful=True)
        print(f"[ok] sdist {sdists[0].name} (v{expected})")
    finally:
        shutil_rmtree(py.parent)
    return 0


def shutil_rmtree(path: Path) -> None:
    import shutil

    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
