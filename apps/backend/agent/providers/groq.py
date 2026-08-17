import json
import logging
import os
from typing import Any, Optional

from packages.llm.clients.groq import GroqClient
from packages.llm.models.prompt import Prompt
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.providers.schema_utils import (
    extract_json_object,
    normalize_tools_for_openai,
)
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class GroqAgentProvider(BaseLLMProvider):
    """
    Agent LLM provider using Groq.com inference API.

    Groq serves OSS models (LLaMA 3.x, Mixtral) via an OpenAI-compatible
    API at ultra-low latency. It has strong native function/tool calling
    support on llama-3.3-70b-versatile.

    Note: This is Groq.com (https://groq.com), not xAI Grok. The xAI Grok
    provider is in grok.py and currently disabled in the production fallback
    chain due to account credential issues.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        api_key_env: str = "GROQ_API_KEY",
        client: Optional[GroqClient] = None,
    ):
        # llama-3.3-70b-versatile: verified working with tool calling (2026-08-15 audit)
        configured_model = os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"
        self.model: str = model or configured_model
        self.client = client or GroqClient(api_key_env=api_key_env)

    def decide(
        self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]
    ) -> AgentDecision:
        # Normalize Gemini-style schema to standard JSON Schema / OpenAI format
        tools_payload = normalize_tools_for_openai(available_tools) if available_tools else []

        system_instruction = (
            "You are the Atlas Agent powered by Groq/LLaMA, an autonomous execution engine for AI benchmarking.\n"
            "Analyze the user's task goal, current plan, and previous tool execution history.\n"
            "CRITICAL: When the execution plan contains pending unexecuted steps, tool calls are MANDATORY.\n"
            "Do NOT return conversational explanations like 'I will create...' or 'I need to create...'. Actually execute the tool call.\n"
            "If the user goal is ambiguous or lacks required information to create or run a benchmark (e.g. 'make a custom benchmark'), "
            "you MUST execute the request_clarification tool instead of guessing or failing.\n"
            "FINAL_RESPONSE text is permitted ONLY when all required plan steps have ALREADY been executed and completed."
        )

        prompt = Prompt(user=prompt_context, system=system_instruction)

        try:
            response = self.client.generate(
                self.model, prompt, tools=tools_payload if tools_payload else None
            )
            raw_choice = (response.raw or {}).get("choices", [{}])[0]
            message = raw_choice.get("message", {})

            # 1. Native Tool Calling (primary path)
            if "tool_calls" in message and message["tool_calls"]:
                tool_call = message["tool_calls"][0].get("function", {})
                tool_name = tool_call.get("name")
                raw_args = tool_call.get("arguments", {})
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                if tool_name:
                    logger.info(f"Groq selected native tool '{tool_name}' with args: {arguments}")
                    return AgentDecision(
                        type=AgentDecisionType.TOOL_CALL,
                        tool_name=tool_name,
                        arguments=arguments,
                        reasoning=f"Groq ({self.model}) selected native tool '{tool_name}'",
                    )

            # 2. Text fallback: extract JSON tool call from content
            content = (message.get("content") or "").strip()
            if content:
                parsed = extract_json_object(content)
                if parsed and "tool_name" in parsed:
                    tool_name = parsed.get("tool_name")
                    arguments = parsed.get("arguments", {})
                    if tool_name:
                        return AgentDecision(
                            type=AgentDecisionType.TOOL_CALL,
                            tool_name=tool_name,
                            arguments=arguments,
                            reasoning=f"Groq ({self.model}) selected tool '{tool_name}' via JSON text",
                        )

            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=content or "No response generated.",
                reasoning=f"Groq ({self.model}) produced text response",
            )

        except Exception as e:
            logger.error(f"GroqAgentProvider error: {e}")
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"Groq provider decision failed: {str(e)}",
            )
