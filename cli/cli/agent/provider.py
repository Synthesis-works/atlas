"""Client-side agent LLM provider adapter (Phase 1).

Wraps ``packages.llm``'s ``GeminiClient`` (already used by the backend agent,
hand-rolled httpx REST client with native Gemini function calling).  This is the
only component that talks to an LLM; the loop consumes the structured
``AgentDecision`` it returns.

Mirrors ``apps/backend/agent/providers/gemini.py``'s raw-response parsing
(functionCall vs text) but as a stateless adapter with no server-side task.
"""

from __future__ import annotations

# ``packages.llm`` lives under the repo root and is a top-level ``packages``
# package (regular package thanks to ``packages/__init__.py``).  Importing it
# requires the repo root (its parent) on ``sys.path``.  We scope that insertion
# here rather than polluting the global site path, so the globally-installed
# ``atlas`` executable and its editable ``cli`` package are unaffected by the
# top-level folder-name layout.
import os  # noqa: E402
import sys  # noqa: E402
from typing import Any

from cli.agent.state import AgentDecision, AgentDecisionType

_ATLAS_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _ATLAS_ROOT not in sys.path:
    sys.path.insert(0, _ATLAS_ROOT)

from packages.llm.clients.gemini import GeminiClient  # noqa: E402
from packages.llm.models.prompt import Prompt  # noqa: E402


class AgentProviderError(Exception):
    """Raised when the agent's LLM brain is unavailable or unreachable."""


class AgentProvider:
    """Adapter that turns a Gemini (tool-calling) response into a decision."""

    def __init__(
        self,
        model: str | None = None,
        api_key_env: str = "GEMINI_API_KEY",
        client: GeminiClient | None = None,
        *,
        available: bool | None = None,
    ) -> None:
        self.model = model or "gemini-3.5-flash-lite"
        self.client = client or GeminiClient(api_key_env=api_key_env)
        # ``available`` is injectable for tests; otherwise derived from the
        # client's key presence (same bias the execution path uses for health).
        if available is None:
            available = self.client.health()
        self.available = available

    def decide(
        self,
        task: str,
        prompt_context: str,
        available_tools: list[dict[str, Any]],
    ) -> AgentDecision:
        """Run one LLM step and return a structured decision.

        ``available_tools`` is the list of Gemini ``functionDeclarations`` for
        the current tool set.  Raises ``AgentProviderError`` when the brain is
        unavailable; surfaces provider/API errors as ``FAIL`` decisions so the
        loop can handle them like any other failure.
        """
        if not self.available:
            raise AgentProviderError(
                "agent brain unavailable: set GEMINI_API_KEY (or AGENT_MODEL for a "
                "custom model) to use the Atlas agent"
            )

        system = (
            "You are the Atlas Agent, a terminal assistant for the Atlas evaluation "
            "platform.\n"
            "Given a user task, call the available tools to inspect benchmarks, models, "
            "runs, and reports. Prefer calling tools to gather facts over guessing.\n"
            "When you have enough information to answer, stop calling tools and return "
            "a concise final response (plain text) summarizing the outcome.\n"
            "If the task is ambiguous or lacks required information, return a "
            "REQUEST_CLARIFICATION-style text asking for what you need."
        )
        prompt = Prompt(user=prompt_context, system=system)

        tools_payload = [{"functionDeclarations": available_tools}] if available_tools else []

        try:
            response = self.client.generate(self.model, prompt, tools=tools_payload)
            raw = response.raw or {}
            candidate = (raw.get("candidates") or [{}])[0]
            parts = (candidate.get("content") or {}).get("parts") or []

            for part in parts:
                if "functionCall" in part:
                    fn = part["functionCall"]
                    return AgentDecision(
                        type=AgentDecisionType.TOOL_CALL,
                        tool_name=fn.get("name"),
                        arguments=fn.get("args") or {},
                        reasoning=f"Gemini selected tool '{fn.get('name')}'",
                    )
                if "text" in part and str(part["text"]).strip():
                    return AgentDecision(
                        type=AgentDecisionType.FINAL_RESPONSE,
                        response=str(part["text"]).strip(),
                        reasoning="Gemini produced a final response",
                    )

            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response="Task completed.",
                reasoning="No tool call or text returned by Gemini.",
            )
        except Exception as exc:  # noqa: BLE001
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"agent provider decision failed: {exc}",
            )
