import urllib.request
import urllib.error
import urllib.parse
import json
import time
import sys

OLLAMA_URL = "http://localhost:11434"

PROMPTS = [
    {
        "name": "Math & Logic",
        "prompt": "Solve this math problem step by step: If a train travels at 60 mph for 2 hours, then 80 mph for 1 hour, what is the average speed for the whole trip?",
    },
    {
        "name": "Creative Writing",
        "prompt": "Write a short 3-sentence story about a robot discovering a forgotten magical library.",
    },
    {
        "name": "Code Generation",
        "prompt": "Write a Python function to calculate the Fibonacci sequence optimally using memoization.",
    },
    {
        "name": "Summarization & Constraints",
        "prompt": "Summarize the history of space exploration in exactly 3 bullet points.",
    },
    {
        "name": "Instruction Formatting (JSON)",
        "prompt": "Provide a JSON object containing keys: 'name', 'age', 'city', and 'occupation' for a fictional character. Respond ONLY with valid JSON.",
    },
]


def check_models():
    print(f"Checking for available models at {OLLAMA_URL}/api/tags...")
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            if not models:
                return None
            return models[0]["name"]
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def pull_tinyllama():
    print("No models found! Pulling 'tinyllama' for benchmarking (this may take a moment)...")
    try:
        data = json.dumps({"name": "tinyllama"}).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/pull", data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            # Consume stream to finish pulling
            for line in resp:
                pass
        print("Successfully pulled 'tinyllama'.")
        return "tinyllama"
    except Exception as e:
        print(f"Failed to pull model: {e}")
        sys.exit(1)


def run_benchmark(model: str, benchmark: dict):
    print(f"\n--- Running Benchmark: {benchmark['name']} ---")
    data = json.dumps({"model": model, "prompt": benchmark["prompt"], "stream": False}).encode(
        "utf-8"
    )

    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate", data=data, headers={"Content-Type": "application/json"}
    )

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=1200) as resp:
            result = json.loads(resp.read().decode())
    except Exception as e:
        print(f"FAILED: {e}")
        return None

    total_time = time.perf_counter() - start_time

    response_text = result.get("response", "").strip()
    eval_count = result.get("eval_count", 0) or 0
    # eval_duration is in nanoseconds, convert to seconds
    eval_duration_s = result.get("eval_duration", 0) / 1e9

    tps = (eval_count / eval_duration_s) if eval_duration_s > 0 else 0

    print(f"Prompt: {benchmark['prompt']}")
    print(f"\nResponse excerpt:\n{response_text[:250]}...\n")
    print(f"Latency: {total_time:.2f}s")
    print(f"Tokens generated: {eval_count}")
    print(f"Generation Speed: {tps:.2f} tokens/sec")

    return {"name": benchmark["name"], "latency": total_time, "tokens": eval_count, "tps": tps}


def main():
    target_models = ["qwen2.5:latest", "gemma2:latest", "mistral:latest", "llama3.2:latest"]
    print(f"\nProceeding to benchmark {len(target_models)} native models across 5 disciplines.")

    all_results = []

    for model in target_models:
        print(f"\n\n{'#' * 60}")
        print(f"### MODEL: {model}")
        print(f"{'#' * 60}")
        for b in PROMPTS:
            res = run_benchmark(model, b)
            if res:
                all_results.append((model, res))

    print("\n\n" + "=" * 85)
    print("GLOBAL BENCHMARK SUMMARY")
    print("=" * 85)
    print(
        f"{'Model':<17} | {'Benchmark Name':<28} | {'Latency (s)':<12} | {'Tokens':<8} | {'Tokens/Sec':<10}"
    )
    print("-" * 85)
    for model, r in all_results:
        print(
            f"{model:<17} | {r['name']:<28} | {r['latency']:<12.2f} | {r['tokens']:<8} | {r['tps']:<10.2f}"
        )
    print("=" * 85)


if __name__ == "__main__":
    main()
