"""Client-side agent LLM provider abstraction (Phase 1, extended in v3.1).

The agent the CLI runs only ever talks to an ``LLMProvider``.  A provider turns
a (possibly tool-calling) LLM response into a structured ``AgentDecision`` for
the loop.  Concretely:

* ``GeminiProvider`` wraps ``packages.llm``'s ``GeminiClient`` (Gemini-native
  ``functionCall`` parts) - the original Phase 1 adapter.
* ``GroqProvider`` wraps ``packages.llm``'s ``GroqClient`` (OpenAI-compatible
  ``message.tool_calls``) - added in v3.1 so the agent is not single-provider.

Providers that implement ``available`` as "this provider is configured (key
present)".  ``decide``:
  * raises ``AgentProviderUnavailableError`` for *transient / genuine availability*
    failures (no key, DNS/network, timeouts, 429 rate-limit, 5xx) - the signal the
    ``ProviderRouter`` uses to try the next provider;
  * returns a ``FAIL`` decision for *non-availability* failures (invalid key /
    auth, invalid request, malformed output) so the loop surfaces them without
    silently bouncing providers.

The loop never needs to know which provider answered; it consumes ``AgentDecision``.
"""

from __future__ import annotations

# ``packages.llm`` is bundled into the ``atlas-cli`` distribution alongside
# ``atlas_sdk`` (see ``cli/pyproject.toml``), so the import is a plain package
# import with no ``sys.path`` manipulation.
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from packages.llm.clients.gemini import GeminiClient
from packages.llm.clients.groq import GroqClient
from packages.llm.models.prompt import Prompt

from cli.agent.state import AgentDecision, AgentDecisionType


class AgentProviderError(Exception):
    """Raised when the agent's LLM brain is unavailable or unreachable."""


class AgentProviderUnavailableError(AgentProviderError):
    """Transient / genuine provider-availability failure (fallback-worthy).

    Raised for: no key configured, DNS/network failure, connection/read timeout,
    provider returned 429 (rate-limit) or 5xx.  Not raised for auth/invalid-key,
    invalid-request, or malformed-output errors (those become ``FAIL`` decisions).
    """


# HTTP status hints used by the availability classifier.  ``429`` and ``5xx``
# mean "this provider is temporarily unable" (fallback-worthy); ``401/403`` mean
# "key/billing invalid" (NOT fallback-worthy - surface it instead of bouncing).
_RATE_SERVER_PATTERN = re.compile(r"\b(429|5\d\d)\b")
_NETWORK_HINTS = (
    "getaddrinfo",
    "winerror",
    "connection",
    "timed out",
    "timeout",
    "request failed",
    "slow down",
    "too many requests",
    "rate limit",
    "rate-limit",
    "server error",
    "service unavailable",
    "unavailable",
)
_AUTH_HINTS = (
    "api key not found",
    "invalid api key",
    "unauthorized",
    "authentication",
    "permission denied",
    "forbidden",
    "401",
    "403",
)


def is_availability_failure(error_message: str) -> bool:
    """True when ``error_message`` describes a transient/availability failure.

    This is the classifier the router consults to decide whether trying the next
    provider is appropriate.  Network/DNS/timeout, 429, and 5xx are availability
    failures; auth/invalid-key and invalid-request are not.
    """
    if not error_message:
        return False
    lowered = error_message.lower()
    if _RATE_SERVER_PATTERN.search(error_message) or any(h in lowered for h in _NETWORK_HINTS):
        return True
    if any(h in lowered for h in _AUTH_HINTS):
        return False
    return False


def _classify_failure(exc: Exception) -> None:
    """Raise ``AgentProviderUnavailableError`` for availability errors, else no-op.

    Returns normally (caller should produce a ``FAIL`` decision) when the error
    is NOT an availability failure.
    """
    if isinstance(exc, AgentProviderUnavailableError):
        raise exc
    if isinstance(exc, AgentProviderError):
        raise exc
    if is_availability_failure(str(exc)):
        raise AgentProviderUnavailableError(str(exc))


def _lower(s: str | None) -> str:
    return (s or "").strip().lower()


# Gemini declares JSON types in UPPERCASE (OBJECT/ARRAY/STRING/...).  Groq speaks
# standard OpenAI JSON-Schema types (object/array/string/...).  Normalize when
# converting the shared Gemini declarations into OpenAI tool definitions.
_GEMINI_TYPE_MAP = {
    "OBJECT": "object",
    "ARRAY": "array",
    "STRING": "string",
    "INTEGER": "integer",
    "NUMBER": "number",
    "BOOLEAN": "boolean",
}


def _normalize_json_schema(schema: Any) -> Any:
    """Recursively lowercase JSON-Schema type keywords (Gemini → OpenAI)."""
    if isinstance(schema, dict):
        out: dict[str, Any] = {}
        for key, value in schema.items():
            if key == "type" and isinstance(value, str):
                out[key] = _GEMINI_TYPE_MAP.get(value.upper(), value.lower())
            else:
                out[key] = _normalize_json_schema(value)
        return out
    if isinstance(schema, list):
        return [_normalize_json_schema(item) for item in schema]
    return schema


class LLMProvider(ABC):
    """A provider of agent-brain responses normalized to ``AgentDecision``."""

    #: short stable id used for ``--provider`` selection ("gemini", "groq", ...)
    name: str = "llm"

    @property
    @abstractmethod
    def available(self) -> bool:
        """True when this provider is configured/usable for this environment."""
        raise NotImplementedError

    @abstractmethod
    def decide(
        self,
        task: str,
        prompt_context: str,
        available_tools: list[dict[str, Any]],
    ) -> AgentDecision:
        """Run one LLM step; return a structured decision."""


class GeminiProvider(LLMProvider):
    """Gemini adapter (native ``functionCall`` parts)."""

    name = "gemini"

    def __init__(
        self,
        model: str | None = None,
        api_key_env: str = "GEMINI_API_KEY",
        client: GeminiClient | None = None,
        *,
        available: bool | None = None,
    ) -> None:
        self.model = model or os.environ.get("AGENT_MODEL") or "gemini-3.5-flash-lite"
        self.client = client or GeminiClient(api_key_env=api_key_env)
        self._available = bool(self.client.health()) if available is None else available

    @property
    def available(self) -> bool:
        return self._available

    @available.setter
    def available(self, value: bool) -> None:
        self._available = bool(value)

    def decide(
        self,
        task: str,
        prompt_context: str,
        available_tools: list[dict[str, Any]],
    ) -> AgentDecision:
        if not self.available:
            raise AgentProviderUnavailableError(
                f"{self.name} brain unavailable: set GEMINI_API_KEY to use it"
            )
        system = _SYSTEM_PROMPT
        prompt = Prompt(user=prompt_context, system=system)
        tools_payload = [{"functionDeclarations": available_tools}] if available_tools else []
        try:
            response = self.client.generate(self.model, prompt, tools=tools_payload)
            return self._parse(response.raw or {})
        except Exception as exc:  # noqa: BLE001
            _classify_failure(exc)
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"agent provider decision failed: {exc}",
            )

    @staticmethod
    def _parse(raw: dict) -> AgentDecision:
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


DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


class GroqProvider(LLMProvider):
    """Groq adapter (OpenAI-compatible ``message.tool_calls``)."""

    name = "groq"

    def __init__(
        self,
        model: str | None = None,
        api_key_env: str = "GROQ_API_KEY",
        client: GroqClient | None = None,
        *,
        available: bool | None = None,
    ) -> None:
        self.model = model or os.environ.get("AGENT_GROQ_MODEL") or DEFAULT_GROQ_MODEL
        self.client = client or GroqClient(api_key_env=api_key_env)
        self._available = bool(self.client.health()) if available is None else available

    @property
    def available(self) -> bool:
        return self._available

    def decide(
        self,
        task: str,
        prompt_context: str,
        available_tools: list[dict[str, Any]],
    ) -> AgentDecision:
        if not self.available:
            raise AgentProviderUnavailableError(
                f"{self.name} brain unavailable: set GROQ_API_KEY (or AGENT_GROQ_MODEL for a "
                "custom model) to use it"
            )
        system = _SYSTEM_PROMPT
        prompt = Prompt(user=prompt_context, system=system)
        # OpenAI-compatible tools: [{ "type":"function", "function": {name, parameters} }]
        tools_payload = []
        for tool in available_tools or []:
            fn: dict[str, Any] = {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
            }
            raw_params = tool.get("parameters")
            if raw_params:
                fn["parameters"] = _normalize_json_schema(raw_params)
            tools_payload.append({"type": "function", "function": fn})
        try:
            response = self.client.generate(self.model, prompt, tools=tools_payload or None)
            return self._parse(response.raw or {})
        except Exception as exc:  # noqa: BLE001
            _classify_failure(exc)
            return AgentDecision(
                type=AgentDecisionType.FAIL,
                error_message=f"agent provider decision failed: {exc}",
            )

    @staticmethod
    def _parse(raw: dict) -> AgentDecision:
        choices = raw.get("choices") or []
        if not choices:
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response="",
                reasoning="No choices returned by Groq.",
            )
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []
        if tool_calls:
            call = tool_calls[0]
            fn = call.get("function") or {}
            args_raw = fn.get("arguments") or "{}"
            args: dict[str, Any] = {}
            if isinstance(args_raw, dict):
                args = args_raw
            else:
                try:
                    import json

                    args = json.loads(args_raw)
                except Exception:  # noqa: BLE001
                    args = {}
            return AgentDecision(
                type=AgentDecisionType.TOOL_CALL,
                tool_name=fn.get("name"),
                arguments=args,
                reasoning=f"Groq selected tool '{fn.get('name')}'",
            )
        text = message.get("content")
        if _lower(text):
            return AgentDecision(
                type=AgentDecisionType.FINAL_RESPONSE,
                response=str(text).strip(),
                reasoning="Groq produced a final response",
            )
        return AgentDecision(
            type=AgentDecisionType.FINAL_RESPONSE,
            response="Task completed.",
            reasoning="No tool call or text returned by Groq.",
        )


# Backward-compatible alias: existing tests construct ``AgentProvider`` directly,
# which has always meant the Gemini adapter.
AgentProvider = GeminiProvider


_SYSTEM_PROMPT = (
    "You are the Atlas Agent, a terminal assistant for the Atlas evaluation "
    "platform.\n"
    "Given a user task, call the available tools to inspect benchmarks, models, "
    "runs, and reports. Prefer calling tools to gather facts over guessing.\n"
    "When you have enough information to answer, stop calling tools and return "
    "a concise final response (plain text) summarizing the outcome.\n"
    "If the task is ambiguous or lacks required information, return a "
    "REQUEST_CLARIFICATION-style text asking for what you need."
)
