import platform
import subprocess
import sys

import psutil


def get_git_commit() -> str:
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return commit.decode("utf-8").strip()
    except Exception:
        return "unknown"


def get_python_version() -> str:
    return sys.version.split(" ")[0]


def get_ollama_version() -> str:
    try:
        ver = subprocess.check_output(["ollama", "--version"], stderr=subprocess.DEVNULL)
        return ver.decode("utf-8").strip().replace("ollama version is ", "")
    except Exception:
        return "unknown"


def get_model_digest(model_name: str) -> str:
    try:
        # e.g., ollama show qwen2.5-coder:1.5b --modelfile or hitting API
        import httpx

        resp = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            for m in models:
                if m["name"] == model_name or m["name"] == f"{model_name}:latest":
                    return m.get("digest", "unknown")
    except Exception:
        pass
    return "unknown"


def get_os_info() -> str:
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def get_cpu_info() -> str:
    return platform.processor()


def get_ram_gb() -> float:
    try:
        return round(psutil.virtual_memory().total / (1024**3), 2)
    except Exception:
        return 0.0


def collect_metadata(model_name: str) -> dict:
    return {
        "git_commit": get_git_commit(),
        "python_version": get_python_version(),
        "ollama_version": get_ollama_version(),
        "model_digest": get_model_digest(model_name),
        "os_info": get_os_info(),
        "cpu_info": get_cpu_info(),
        "ram_gb": get_ram_gb(),
        "atlas_version": "0.2.0",
    }
