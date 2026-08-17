import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from packages.llm.clients.grok import GrokClient
from packages.llm.models.prompt import Prompt
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.schema_utils import normalize_tools_for_openai
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
        self.model: str = model or os.getenv("GROK_MODEL") or os.getenv("XAI_MODEL") or "grok-2"
        self.client = client or GrokClient(api_key_env=api_key_env)

    def decide(
        self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]
    ) -> AgentDecision:
        # Normalize Gemini-style UPPERCASE types to JSON Schema lowercase before sending to xAI
        tools_payload = normalize_tools_for_openai(available_tools) if available_tools else []

        system_instruction = (
            "You are the Atlas Agent powered by xAI Grok, an autonomous execution engine for AI benchmarking.\n"
            "Analyze the user's task goal, current plan, and previous tool execution history.\n"
            "CRITICAL: When the execution plan contains pending unexecuted steps, tool calls are MANDATORY.\n"
            "Do NOT return conversational explanations like 'I will create...' or 'I need to create...'. Actually execute the tool call.\n"
            "If the user goal is ambiguous or lacks required information to create or run a benchmark (e.g. 'make a custom benchmark'), you MUST execute the request_clarification tool instead of guessing or failing.\n"
            "FINAL_RESPONSE text is permitted ONLY when all required plan steps have ALREADY been executed and completed."
        )

        prompt = Prompt(user=prompt_context, system=system_instruction)

        try:
            start_t = time.time()
            response = self.client.generate(self.model, prompt, tools=tools_payload)
            latency = int((time.time() - start_t) * 1000)

            raw = response.raw or {}
            raw_choice = raw.get("choices", [{}])[0]
            message = raw_choice.get("message", {})

            # 1. Native Tool Calling Response Parsing
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0].get("function", {})
                tool_name = tool_call.get("name")
                raw_args = tool_call.get("arguments", {})
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                if tool_name:
                    logger.info(f"Grok selected native tool '{tool_name}' with args: {arguments}")
                    return AgentDecision(
                        type=AgentDecisionType.TOOL_CALL,
                        tool_name=tool_name,
                        arguments=arguments,
                        reasoning=f"Grok selected native tool '{tool_name}'",
                    )

            # 2. Secondary Fallback: Regex JSON extraction from content
            content = (message.get("content") or "").strip()
            if content:
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
                                reasoning=f"Grok selected tool '{tool_name}' via JSON text",
                            )
                    except Exception:
                        pass

            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=content or "No response generated.",
                reasoning="Grok produced text response",
            )

        except Exception as e:
            logger.error(f"GrokAgentProvider error: {e}")
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"Grok provider decision failed: {str(e)}",
            )
