import urllib.request
import json

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
        "name": "Instruction Formatting (JSON)",
        "prompt": "Provide a JSON object containing keys: 'name', 'age', 'city', and 'occupation' for a fictional character. Respond ONLY with valid JSON.",
    },
]

target_models = ["qwen2.5:latest", "mistral:latest", "llama3.2:latest"]

with open("traces.md", "w", encoding="utf-8") as f:
    f.write("# Detailed LLM Benchmark Traces\n\n")

for model in target_models:
    print(f"Tracing {model}...")
    with open("traces.md", "a", encoding="utf-8") as f:
        f.write(f"## Model: {model}\n\n")
    for prompt_obj in PROMPTS:
        data = {
            "model": model,
            "prompt": prompt_obj["prompt"],
            "stream": False,
            "options": {
                "num_predict": 120  # Fast cutoff limit to save processing time
            },
        }
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

        response_text = ""
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                result = json.loads(resp.read().decode())
                response_text = result.get("response", "").strip()
        except Exception as e:
            response_text = f"[FAILED TO GENERATE: {str(e)}]"

        with open("traces.md", "a", encoding="utf-8") as f:
            f.write(f"### Prompt: {prompt_obj['name']}\n")
            f.write(f"**Input**:\n> {prompt_obj['prompt']}\n\n")
            f.write(f"**Output**:\n```text\n{response_text}\n```\n\n---\n")

print("Done generating traces.")
