import time

from .base import BaseModelAdapter, PredictionResult


class MockModelAdapter(BaseModelAdapter):
    def predict(self, prompt_text: str) -> PredictionResult:
        """
        Mock prediction that echoes a predictable output.
        In a real scenario, this might sleep to simulate latency.
        """
        start = time.perf_counter()
        # For our exact match exact tests, it's helpful if the mock adapter
        # can just echo something predictable. Or perhaps we just return
        # a standard text.
        output_text = "mocked_output"

        # If the prompt contains a specific instruction to echo, we can do it,
        # but for simplicity, we just return a fixed string.
        # For integration testing, this is enough to prove the pipeline works.
        latency = int((time.perf_counter() - start) * 1000)

        return PredictionResult(
            output_text=output_text,
            latency_ms=latency,
            token_usage=10,
            raw_response={"status": "mocked", "prompt": prompt_text},
        )
