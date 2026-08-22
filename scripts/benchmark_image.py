"""Build and smoke-test the Atlas benchmark execution image.

Usage:
    python scripts/benchmark_image.py build [--tag TAG]
    python scripts/benchmark_image.py smoke [--tag TAG]

`build`  : docker build docker/benchmark -> atlas-benchmark-runner:<tag>
`smoke`  : run the image with network_mode=none, a mock-target payload, and
           assert the container emits the expected JSON output line. Proves
           the runtime closure is complete WITHOUT any egress or secrets.

The smoke test is fully offline (mock adapter) so it doubles as a CI gate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid

DEFAULT_TAG = "atlas-benchmark-runner:smoke"


def _docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"docker {' '.join(args)} failed with code {result.returncode}")
    return result.stdout


def build(tag: str) -> None:
    _docker(
        "build",
        "-f",
        "docker/benchmark/Dockerfile",
        "-t",
        tag,
        ".",
    )
    print(f"[benchmark-image] built {tag}")


def smoke(tag: str) -> None:
    payload = {
        "execution_id": str(uuid.uuid4()),
        "attempt_id": str(uuid.uuid4()),
        "attempt_number": 1,
        "target_model": "mock",
        "benchmark_version_id": str(uuid.uuid4()),
        "dataset_version_id": None,
        "test_cases": [
            {
                "id": "tc-1",
                "input_data": {"text": "hello"},
                "task": {"prompts": [{"template": "Echo: {text}"}]},
            }
        ],
        "execution_config": {},
        "correlation_id": "image-smoke",
        "trace_id": "image-smoke",
        "worker_id": "scripts",
    }

    out = _docker(
        "run",
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--memory",
        "256m",
        "--pids-limit",
        "32",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--tmpfs",
        "/workspace:rw,noexec,nosuid,size=32m",
        "-w",
        "/workspace",
        "-e",
        f"ATLAS_EXECUTION_PAYLOAD={json.dumps(payload)}",
        tag,
    )

    lines = [line for line in out.strip().splitlines() if line.strip()]
    parsed = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    outputs = [p for p in parsed if p.get("test_case_id") == "tc-1"]
    if not outputs:
        print(out)
        raise SystemExit("[benchmark-image] SMOKE FAILED: no JSON output line for tc-1")

    got = outputs[0].get("output")
    if got != "mocked_output":
        print(out)
        raise SystemExit(f"[benchmark-image] SMOKE FAILED: expected 'mocked_output', got {got!r}")

    print("[benchmark-image] SMOKE PASSED (offline, mock target):")
    print(json.dumps(outputs[0], indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "smoke"])
    parser.add_argument("--tag", default=DEFAULT_TAG)
    args = parser.parse_args()

    if args.command == "build":
        build(args.tag)
    else:
        # smoke implies the image exists; build first if missing.
        check = subprocess.run(
            ["docker", "image", "inspect", args.tag],
            capture_output=True,
        )
        if check.returncode != 0:
            build(args.tag)
        smoke(args.tag)


if __name__ == "__main__":
    main()
