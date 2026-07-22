import abc
from typing import Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class BaseJudgeAdapter(abc.ABC):
    """
    Isolates external LLM providers from the Evaluation Engine.
    """
    @abc.abstractmethod
    def ask(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        pass

class MockJudgeAdapter(BaseJudgeAdapter):
    """
    Mock adapter for Phase C.3 to prove the architecture.
    """
    def ask(self, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        logger.info("MockJudgeAdapter invoked", prompt_length=len(prompt))
        return {
            "passed": True,
            "confidence": 0.95,
            "reasoning": "This is a mock judge response.",
            "raw_provider_response": {"fake_token_count": 42}
        }
