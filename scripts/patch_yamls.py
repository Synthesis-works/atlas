import os

import yaml

custom_dir = r"C:\Users\Sujal\.gemini\antigravity\worktrees\atlas\implement-benchmark-foundation\benchmarks\coding\custom"
for filename in os.listdir(custom_dir):
    if not filename.endswith(".yaml"):
        continue
    filepath = os.path.join(custom_dir, filename)
    with open(filepath) as f:
        data = yaml.safe_load(f)

    for task in data.get("tasks", []):
        if filename == "binary_search.yaml" or filename == "fibonacci.yaml":
            task["evaluation"] = {
                "extractor": "noop",
                "normalizer": "noop",
                "judge": "numeric_match",
                "metrics": ["accuracy", "latency"],
            }
        elif filename == "fizzbuzz.yaml":
            task["evaluation"] = {
                "extractor": "code_block",
                "normalizer": "whitespace",
                "judge": "exact_match",
                "metrics": ["accuracy", "latency"],
            }
        else:
            task["evaluation"] = {
                "extractor": "noop",
                "normalizer": "lowercase",
                "judge": "exact_match",
                "metrics": ["accuracy", "latency"],
            }

    with open(filepath, "w") as f:
        yaml.dump(data, f, sort_keys=False)
