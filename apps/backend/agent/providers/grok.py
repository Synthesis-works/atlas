import json
import logging, os, time
from typing import Any, Dict, List, Optional

from packages.llm.clients.grok import GrokClient
from packages.llm.models.prompt import Prompt
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class GrokAgentProvider(BaseLLMProvider):
    """
    Agent LLM provider using xAI Grok (grok-2-latest).
    Normalizes response output into AgentDecision.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key_env: str = "XAI_API_KEY",
        client: Optional[GrokClient] = None,
    ):
        self.model = model or os.getenv("GROK_MODEL", os.getenv("XAI_MODEL", "grok-2"))
        self.client = client or GrokClient(api_key_env=api_key_env)

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]) -> AgentDecision:
        tool_descriptions = []
        for t in available_tools:
            name = t.get("name")
            desc = t.get("description")
            params = t.get("parameters", {}).get("properties", {})
            tool_descriptions.append(f"- {name}: {desc}. Parameters: {json.dumps(params)}")

        tools_summary = "\n".join(tool_descriptions)

        system_instruction = (
            "You are the Atlas Agent powered by xAI Grok, an autonomous execution engine for AI benchmarking.\n"
            "Analyze the user's task goal, current plan, and previous tool execution history.\n"
            "CRITICAL: When the execution plan contains pending unexecuted steps (e.g., benchmark creation, dataset generation, model execution, evaluation, report), tool calls are MANDATORY.\n"
            "Do NOT return conversational explanations like 'I will create...' or 'I need to create...'. Actually execute the tool call.\n"
            "Return ONLY a JSON object formatted as: {\"tool_name\": \"<name>\", \"arguments\": {<args>}}\n"
            "FINAL_RESPONSE text is permitted ONLY when all required plan steps have ALREADY been executed and completed.\n"
            f"AVAILABLE TOOLS:\n{tools_summary}"
        )

        prompt = Prompt(user=prompt_context, system=system_instruction)

        try:
            start_t = time.time()
            response = self.client.generate(self.model, prompt)
            latency = int((time.time() - start_t) * 1000)

            content = response.response.strip()

            # Robust JSON extraction from markdown code fences or raw text
            import re
            json_str = content
            if "```" in content:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                if match:
                    json_str = match.group(1)
            elif "{" in content and "}" in content:
                match = re.search(r"(\{.*?\})", content, re.DOTALL)
                if match:
                    json_str = match.group(1)

            if "tool_name" in json_str:
                try:
                    data = json.loads(json_str)
                    tool_name = data.get("tool_name")
                    arguments = data.get("arguments", {})
                    if tool_name:
                        return AgentDecision(
                            type=AgentDecisionType.TOOL_CALL,
                            tool_name=tool_name,
                            arguments=arguments,
                            reasoning=f"Grok selected tool '{tool_name}'",
                        )
                except Exception:
                    pass

            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=content,
                reasoning="Grok produced text response",
            )

        except Exception as e:
            logger.error(f"GrokAgentProvider error: {e}")
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"Grok provider decision failed: {str(e)}",
            )
