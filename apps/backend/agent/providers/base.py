from abc import ABC, abstractmethod
from typing import Any, Dict, List

from apps.backend.agent.state import AgentDecision, AgentTask


class BaseLLMProvider(ABC):
    @abstractmethod
    def decide(self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]) -> AgentDecision:
        """
        Given the task state, prompt context, and available tool schemas,
        returns an AgentDecision (TOOL_CALL, FINAL_RESPONSE, REPLAN, REQUEST_APPROVAL, or FAIL).
        """
        pass
