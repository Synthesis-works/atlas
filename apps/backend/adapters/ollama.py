import time
import json
import urllib.request
import urllib.error
from .base import BaseModelAdapter, PredictionResult
from apps.backend.config import settings


class OllamaAdapter(BaseModelAdapter):
    def __init__(self, target_model: str = None):
        self.base_url = settings.ollama_base_url
        self.model = target_model or settings.ollama_default_model
        self.timeout = settings.ollama_timeout

    def predict(self, prompt_text: str) -> PredictionResult:
        start = time.perf_counter()

        request_data = {"model": self.model, "prompt": prompt_text, "stream": False}
        data = json.dumps(request_data).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate", data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())

            latency = int((time.perf_counter() - start) * 1000)

            return PredictionResult(
                output_text=result.get("response", ""),
                latency_ms=latency,
                token_usage=result.get("eval_count", 0) or 0,
                raw_response=result,
            )
        except urllib.error.URLError as e:
            latency = int((time.perf_counter() - start) * 1000)
            return PredictionResult(
                output_text=f"Error: Could not reach Ollama at {self.base_url} (or model {self.model} not available): {e}",
                latency_ms=latency,
                token_usage=0,
                raw_response={"error": str(e), "status": "failed"},
            )

    @classmethod
    def get_available_models(cls) -> list[dict]:
        """
        Pings the Ollama instance for the list of available tags/models.
        """
        base_url = settings.ollama_base_url
        timeout = 5
        req = urllib.request.Request(f"{base_url}/api/tags")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode())
                models = result.get("models", [])

                formatted_models = []
                for m in models:
                    formatted_models.append(
                        {
                            "id": f"ollama/{m['name']}",
                            "name": m["name"],
                            "provider": "ollama",
                            "size": m.get("size", 0),
                            "status": "operational",
                        }
                    )
                return formatted_models
        except urllib.error.URLError:
            return []
