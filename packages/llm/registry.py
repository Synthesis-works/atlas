import os
import logging
from typing import Any, Dict, List
import httpx

from packages.llm.clients.ollama import OllamaClient
from packages.llm.config import OLLAMA_HOST

logger = logging.getLogger(__name__)


class ModelRegistry:
    @staticmethod
    def get_all_models() -> List[Dict[str, Any]]:
        models = []

        # 1. Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        models.append({
            "provider": "gemini",
            "model": "gemini-3.5-flash-lite",
            "display_name": "Gemini 3.5 Flash Lite",
            "source": "cloud",
            "available": bool(gemini_key),
            "status": "AVAILABLE" if gemini_key else "NOT_CONFIGURED",
            "capabilities": ["chat", "reasoning"]
        })
        models.append({
            "provider": "gemini",
            "model": "gemini-3.1-flash-lite",
            "display_name": "Gemini 3.1 Flash Lite",
            "source": "cloud",
            "available": bool(gemini_key),
            "status": "AVAILABLE" if gemini_key else "NOT_CONFIGURED",
            "capabilities": ["chat", "reasoning"]
        })

        # 2. Grok
        grok_key = os.getenv("XAI_API_KEY")
        models.append({
            "provider": "grok",
            "model": "grok-2-latest",
            "display_name": "Grok 2 Latest",
            "source": "cloud",
            "available": bool(grok_key),
            "status": "AVAILABLE" if grok_key else "NOT_CONFIGURED",
            "capabilities": ["chat", "reasoning"]
        })

        # 3. Mistral
        mistral_key = os.getenv("MISTRAL_API_KEY")
        models.append({
            "provider": "mistral",
            "model": "mistral-small-latest",
            "display_name": "Mistral Small Latest",
            "source": "cloud",
            "available": bool(mistral_key),
            "status": "AVAILABLE" if mistral_key else "NOT_CONFIGURED",
            "capabilities": ["chat", "reasoning"]
        })

        # 4. OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        models.append({
            "provider": "openai",
            "model": "gpt-4o",
            "display_name": "GPT-4o",
            "source": "cloud",
            "available": bool(openai_key),
            "status": "AVAILABLE" if openai_key else "NOT_CONFIGURED",
            "capabilities": ["chat", "reasoning"]
        })

        # 5. Groq
        groq_key = os.getenv("GROQ_API_KEY")
        models.append({
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "display_name": "Llama 3.3 70b (Groq)",
            "source": "cloud",
            "available": bool(groq_key),
            "status": "AVAILABLE" if groq_key else "NOT_CONFIGURED",
            "capabilities": ["chat"]
        })

        # 6. Nvidia
        nvidia_key = os.getenv("NVIDIA_API_KEY")
        models.append({
            "provider": "nvidia",
            "model": "meta/llama-3.1-405b-instruct",
            "display_name": "Llama 3.1 405b (Nvidia)",
            "source": "cloud",
            "available": bool(nvidia_key),
            "status": "AVAILABLE" if nvidia_key else "NOT_CONFIGURED",
            "capabilities": ["chat"]
        })

        # 7. Ollama Local Discovery (non-blocking connection timeout)
        try:
            # Quick check if Ollama is running before listing
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(OLLAMA_HOST)
                is_ollama_alive = resp.status_code == 200
        except Exception:
            is_ollama_alive = False

        if is_ollama_alive:
            try:
                ollama_client = OllamaClient()
                list_info = ollama_client.list_models()
                for m in list_info:
                    if "embed" in m.name.lower() or "nomic" in m.name.lower():
                        continue
                    models.append({
                        "provider": "ollama",
                        "model": m.name,
                        "display_name": f"{m.name} (Local)",
                        "source": "local",
                        "available": True,
                        "status": "AVAILABLE",
                        "capabilities": ["chat"]
                    })
            except Exception as e:
                logger.warning(f"Ollama list failed: {e}")
        else:
            # Add an offline marker entry
            models.append({
                "provider": "ollama",
                "model": "ollama-offline",
                "display_name": "Ollama (Offline)",
                "source": "local",
                "available": False,
                "status": "OFFLINE",
                "capabilities": []
            })

        # 8. Mock (always available for development/testing)
        models.append({
            "provider": "mock",
            "model": "mock",
            "display_name": "Mock Model",
            "source": "local",
            "available": True,
            "status": "AVAILABLE",
            "capabilities": ["chat"]
        })

        return models
