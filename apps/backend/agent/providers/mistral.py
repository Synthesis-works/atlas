import json
import logging, os, time
from typing import Any, Dict, List, Optional

from packages.llm.clients.mistral import MistralClient
from packages.llm.models.prompt import Prompt
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class MistralAgentProvider(BaseLLMProvider):
    """
    Agent LLM provider using Mistral AI (mistral-small-latest).
    Normalizes response output into AgentDecision.
    """

    def __init__(
        self,
        model: str = "mistral-small-latest",
        api_key_env: str = "MISTRAL_API_KEY",
        client: Optional[MistralClient] = None,
    ):
        self.model = model
        self.client = client or MistralClient(api_key_env=api_key_env)

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]) -> AgentDecision:
        tool_descriptions = []
        for t in available_tools:
            name = t.get("name")
            desc = t.get("description")
            params = t.get("parameters", {}).get("properties", {})
            tool_descriptions.append(f"- {name}: {desc}. Parameters: {json.dumps(params)}")

        tools_summary = "\n".join(tool_descriptions)

        system_instruction = (
            "You are the Atlas Agent powered by Mistral AI, an autonomous orchestration engine for AI benchmarking.\n"
            "Analyze the user's task goal, current plan, and previous tool execution history.\n"
            "If an action is needed, return a JSON object with keys 'tool_name' and 'arguments'.\n"
            "If all necessary actions are completed, return a concise final text response.\n"
            f"AVAILABLE TOOLS:\n{tools_summary}\n"
            "Output JSON format for tool call: {\"tool_name\": \"<name>\", \"arguments\": {<args>}}"
        )

        prompt = Prompt(user=prompt_context, system=system_instruction)

        try:
            start_t = time.time()
            response = self.client.generate(self.model, prompt)
            latency = int((time.time() - start_t) * 1000)

            content = response.response.strip()

            if content.startswith("{") and "tool_name" in content:
                try:
                    data = json.loads(content)
                    tool_name = data.get("tool_name")
                    arguments = data.get("arguments", {})
                    if tool_name:
                        return AgentDecision(
                            type=AgentDecisionType.TOOL_CALL,
                            tool_name=tool_name,
                            arguments=arguments,
                            reasoning=f"Mistral selected tool '{tool_name}'",
                        )
                except Exception:
                    pass

            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=content,
                reasoning="Mistral produced final text response",
            )

        except Exception as e:
            logger.error(f"MistralAgentProvider error: {e}")
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"Mistral provider decision failed: {str(e)}",
            )
