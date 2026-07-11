import json
import urllib.request
import urllib.error
from typing import Dict, Any

class InsightGenerator:
    """
    Evidence-first insight generator.
    Feeds strictly structured metrics/clusters into the LLM to prevent hallucination.
    """
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        
    def generate(self, evidence: Dict[str, Any], model: str = "qwen2.5-coder:1.5b") -> str:
        system = (
            "You are a strict data analyst. You are provided with structured evidence from an AI benchmark experiment. "
            "Your job is to read this evidence and generate 3 to 5 bullet points of clear, factual insights. "
            "DO NOT invent numbers. DO NOT hallucinate statistics. Base your insights strictly on the provided evidence JSON."
        )
        
        evidence_str = json.dumps(evidence, indent=2)
        user = f"Evidence Data:\n{evidence_str}\n\nPlease generate concise factual insights."
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        
        try:
            req = urllib.request.Request(f"{self.host}/api/chat", json.dumps(payload).encode('utf-8'), {'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('message', {}).get('content', '')
        except Exception as e:
            return f"*Error generating insights: {e}*"
