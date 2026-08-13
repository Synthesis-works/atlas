import json
import logging
from typing import Any, Dict, List, Optional

from packages.llm.clients.gemini import GeminiClient
from packages.llm.models.prompt import Prompt
from apps.backend.agent.providers.base import BaseLLMProvider
from apps.backend.agent.state import AgentDecision, AgentDecisionType, AgentTask

logger = logging.getLogger(__name__)


class GeminiAgentProvider(BaseLLMProvider):
    """
    Agent LLM provider relying on native Gemini function calling.
    Uses GeminiClient and sends tool functionDeclarations directly in generateContent payload.
    """

    def __init__(
        self,
        model: str = "gemini-3.5-flash-lite",
        api_key_env: str = "GEMINI_API_KEY",
        client: Optional[GeminiClient] = None,
    ):
        self.model = model
        self.client = client or GeminiClient(api_key_env=api_key_env)

    def decide(self, task: AgentTask, prompt_context: str, available_tools: list[dict[str, Any]]) -> AgentDecision:
        system_instruction = (
            "You are the Atlas Agent, an autonomous orchestration engine for AI benchmarking and evaluation.\n"
            "Analyze the user's task goal, current plan, and tool execution history.\n"
            "Execute necessary tools in sequential workflow steps without repeating redundant search calls:\n"
            "1. get_available_models\n"
            "2. create_benchmark (or search_benchmarks)\n"
            "3. create_dataset for the benchmark\n"
            "4. create_evaluation_case: SELECT APPROPRIATE METHOD DYNAMICALLY:\n"
            "   - Deterministic tasks (arithmetic, exact facts): use evaluation_method='exact_match' or 'numeric'.\n"
            "   - Open-ended / conversational tasks (greetings, explanations, summarization): MUST use evaluation_method='llm_judge' or 'rubric', set expected_answer='Provide a friendly greeting', and provide rubric_criteria: ['Responds with a friendly greeting', 'Friendly and helpful tone', 'Appropriate response']. NEVER use exact_match for open-ended tasks!\n"
            "5. validate_benchmark_dataset\n"
            "6. run_benchmark against target models\n"
            "7. evaluate_run to compute metrics using evaluation cases\n"
            "8. generate_report to summarize findings\n"
            "9. request_clarification: Call this tool if the user's goal is ambiguous, underspecified, or lacks required information to create or run a benchmark (e.g. 'make a custom benchmark'), instead of failing or guessing.\n"
            "When all required steps are completed, return a concise final text response summarizing your actions."
        )

        # Convert tool schemas into Gemini functionDeclarations format
        tools_payload = []
        if available_tools:
            tools_payload = [{"functionDeclarations": available_tools}]

        import time
        prompt = Prompt(user=prompt_context, system=system_instruction)

        max_internal_attempts = 1
        for attempt in range(max_internal_attempts + 1):
            try:
                response = self.client.generate(self.model, prompt, tools=tools_payload)
                raw_candidate = response.raw.get("candidates", [{}])[0]
                parts = raw_candidate.get("content", {}).get("parts", [])

                for part in parts:
                    if "functionCall" in part:
                        fn = part["functionCall"]
                        tool_name = fn.get("name")
                        args = fn.get("args", {})
                        logger.info(f"Gemini selected tool '{tool_name}' with args: {args}")
                        return AgentDecision(
                            type=AgentDecisionType.TOOL_CALL,
                            tool_name=tool_name,
                            arguments=args,
                            reasoning=f"Gemini selected tool '{tool_name}'",
                        )
                    elif "text" in part:
                        text_content = part["text"].strip()
                        if text_content:
                            return AgentDecision(
                                type=AgentDecisionType.FINAL_RESPONSE,
                                response=text_content,
                                reasoning="Gemini produced final response",
                            )

                return AgentDecision(
                    type=AgentDecisionType.FINAL_RESPONSE,
                    response="Task completed.",
                    reasoning="No further tool call or response returned by Gemini.",
                )

            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "503" in err_str or "quota" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_internal_attempts:
                    sleep_time = 1.0
                    logger.warning(f"Gemini API rate limit/unavailable. Retrying internal attempt {attempt + 1} in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue

                logger.error(f"GeminiAgentProvider error: {e}")
                return AgentDecision(
                    type=AgentDecisionType.FAIL,
                    error_message=f"Gemini provider decision failed: {str(e)}",
                )
