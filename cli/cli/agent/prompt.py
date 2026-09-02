"""Client-side agent prompt builder (Phase 3).

Renders the per-turn ``prompt_context`` string handed to the provider so Gemini
sees the user's goal plus the evolving tool-call/observation transcript.  The
backend drives its loop the same way (task + plan + tool execution history as a
rendered context), which lets the CLI loop send observations back without
requiring a multi-turn-native provider API.
"""

from __future__ import annotations

from typing import Any

from cli.agent.state import AgentContext, ObservationRecord, ToolCallRecord

_MAX_TRANSCRIPT = 12
_MAX_HISTORY = 8


def _tool_call_line(call: ToolCallRecord) -> str:
    args = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
    return f"tool call: {call.tool_name}({args})"


def _result_summary(output: Any) -> str:
    if isinstance(output, dict) and "summary" in output:
        return str(output["summary"])
    if isinstance(output, Exception):
        return str(output)
    return str(output)


def _observation_line(obs: ObservationRecord) -> str:
    if not obs.success:
        return f"  result: ERROR — {obs.error or 'tool failed'}"
    return f"  result: {_result_summary(obs.output)}"


def build_context(
    context: AgentContext,
    *,
    conversation_history: list[tuple[str, str]] | None = None,
) -> str:
    """Render the user goal and recent tool transcript for the LLM.

    ``conversation_history`` is an optional list of prior ``(user, assistant)``
    turns from an interactive session, so the agent can reference earlier
    context across REPL turns.  It is prepended, bounded, and omitted for
    one-shot runs (where it is None).
    """
    lines: list[str] = []

    if conversation_history:
        lines.append("Earlier in this conversation:")
        for user_text, assistant_text in conversation_history[-_MAX_HISTORY:]:
            lines.append(f"  you: {user_text}")
            lines.append(f"  atlas: {assistant_text}")
        lines.append("")

    lines.append(f"User goal: {context.goal}")

    calls = context.tool_calls[-_MAX_TRANSCRIPT:]
    obs_by_call = {o.call_id: o for o in context.observations}
    for call in calls:
        lines.append(_tool_call_line(call))
        obs = obs_by_call.get(call.call_id)
        if obs is not None:
            lines.append(_observation_line(obs))

    if not calls:
        lines.append("(no tools called yet — the goal is still ahead)")

    return "\n".join(lines)
