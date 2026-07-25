import json
import urllib.error
import urllib.request

from packages.evaluation.extractors.code_block import CodeBlockExtractor

from .base_repair import BaseRepairAgent


class OllamaRepairAgent(BaseRepairAgent):
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host

    def generate_repair(
        self, task_id: str, original_prompt: str, failed_code: str, error_message: str, model: str
    ) -> str | None:
        system = (
            "You are an expert Python debugger. The user has provided an original prompt, a buggy Python solution, "
            "and the error message or traceback that resulted from running it. "
            "Your task is to fix the code so that it satisfies the original prompt and avoids the error. "
            "Output ONLY the corrected valid Python code. Do not explain your answer. Do not include markdown formatting if possible, "
            "or if you do, wrap it strictly in a python code block."
        )

        user = f"Original Prompt:\n{original_prompt}\n\nBuggy Code:\n{failed_code}\n\nError Message:\n{error_message}\n\nPlease fix the buggy code."

        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2},
        }

        try:
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                json.dumps(payload).encode("utf-8"),
                {"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                raw_response = result.get("message", {}).get("content", "")
                extractor = CodeBlockExtractor()
                extracted = extractor.extract(raw_response)
                return extracted
        except Exception as e:
            print(f"[OllamaRepairAgent] Error generating repair: {e}")
            return None
