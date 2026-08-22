"""Container entry point for DockerExecutor.

This module runs INSIDE the benchmark container. It receives the execution payload
via environment variable ATLAS_EXECUTION_PAYLOAD, runs the benchmark using the
same logic as ExecutionRunner, and outputs JSON lines for each model output.

The container should be built with an image that includes:
- All Atlas dependencies (via uv sync)
- The benchmark code
- LLM provider SDKs (openai, anthropic, etc.)
"""

import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

# Add the app directory to path so imports work
sys.path.insert(0, "/app")

from apps.backend.adapters.factory import AdapterFactory
from apps.backend.worker.prompt_resolver import PromptResolver


def main() -> int:
    """Run the benchmark execution inside the container."""
    payload_str = os.environ.get("ATLAS_EXECUTION_PAYLOAD")
    if not payload_str:
        print("ERROR: ATLAS_EXECUTION_PAYLOAD not set", file=sys.stderr)
        return 1

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON payload: {e}", file=sys.stderr)
        return 1

    execution_id = payload.get("execution_id")
    attempt_id = payload.get("attempt_id")
    target_model = payload.get("target_model")
    test_cases = payload.get("test_cases", [])
    execution_config = payload.get("execution_config", {})

    if not all([execution_id, attempt_id, target_model]):
        print("ERROR: Missing required fields in payload", file=sys.stderr)
        return 1

    try:
        adapter = AdapterFactory.get_adapter(target_model)
        resolver = PromptResolver()

        for test_case in test_cases:
            task = test_case.get("task")
            if not task:
                continue
            prompts = task.get("prompts", [])
            prompt_template = prompts[0].get("template", "{text}") if prompts else "{text}"

            hydrated_prompt = resolver.resolve(prompt_template, test_case.get("input_data", {}))

            try:
                prediction_result = adapter.predict(hydrated_prompt)
            except Exception as e:
                # Output error for this test case but continue
                output = {
                    "test_case_id": test_case.get("id"),
                    "output": f"ERROR: {e}",
                    "latency_ms": 0,
                    "tokens": 0,
                    "error": str(e),
                }
                print(json.dumps(output), flush=True)
                continue

            # Output JSON line for each model output
            output = {
                "test_case_id": test_case.get("id"),
                "output": prediction_result.output_text,
                "latency_ms": prediction_result.latency_ms,
                "tokens": prediction_result.token_usage,
            }
            print(json.dumps(output), flush=True)

        return 0

    except Exception as e:
        print(f"ERROR: Execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
