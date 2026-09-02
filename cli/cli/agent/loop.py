"""Client-side agent loop (Phase 3).

The loop orchestrates one agent run:

    decision
      -> FINAL_RESPONSE            -> return
      -> TOOL_CALL                 -> validate + dispatch via ToolRegistry
      -> record ToolCallRecord
      -> record ObservationRecord
      -> render observation back into prompt_context
      -> repeat

It enforces the Phase 1 hard limits (steps, tool-call ceiling, wall-clock
deadline) deterministically with the authoritative ``GoalExceededError``
machinery, and converts unknown-tool / malformed-argument / tool-exception
failures into failing observations the LLM can reason about — never letting a
Python traceback escape to the user.

Mutation confirmation (Phase 4): an injectable ``confirm`` callback gates WRITE
tools before dispatch.  When it returns False, the tool is NOT executed and a
structured "declined" observation is recorded so the agent knows the user
declined rather than treating it as an execution failure.  The default
(``confirm=None``) auto-approves — used by non-interactive one-shot mode.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from cli.agent.prompt import build_context
from cli.agent.state import (
    AGENT_DEADLINE_SECONDS,
    AgentContext,
    AgentDecision,
    AgentDecisionType,
    GoalExceededError,
    ToolCallRecord,
)
from cli.agent.tools.registry import ToolRegistry


class AgentResult(BaseModel):
    """Terminal outcome of a single agent run."""

    ok: bool
    response: str | None = None
    error: str | None = None
    needs_clarification: bool = False


class AgentLoop:
    """Drives a client-side agent run over a provider, tool registry, and client."""

    def __init__(
        self,
        provider: object,
        *,
        registry: ToolRegistry | None = None,
        client: object,
        context: AgentContext | None = None,
        now: Callable[[], datetime] | None = None,
        confirm: Callable[[str, dict], bool] | None = None,
        on_tool: Callable[[ToolCallRecord, Any], None] | None = None,
        conversation_history: list[tuple[str, str]] | None = None,
    ) -> None:
        self.provider = provider
        self.registry = registry or ToolRegistry()
        self.client = client
        self.context = context
        self._now = now or (lambda: datetime.now(UTC))
        # ``confirm`` gates WRITE tools; None auto-approves (one-shot).
        self._confirm = confirm
        # ``on_tool`` fires after each tool call for REPL progress display.
        self._on_tool = on_tool
        self._conversation_history = conversation_history

    def _reset_context(self, task: str) -> None:
        if self.context is None:
            self.context = AgentContext(goal=task, started_at=self._now())

    def _check_deadline(self) -> None:
        assert self.context is not None
        elapsed = (self._now() - self.context.started_at).total_seconds()
        if elapsed >= AGENT_DEADLINE_SECONDS:
            raise GoalExceededError(
                f"deadline ({AGENT_DEADLINE_SECONDS}s) exceeded"
            )

    def _dispatch(self, decision: AgentDecision) -> None:
        """Record + execute one tool call, capturing failures as observations."""
        assert self.context is not None
        tool_name = decision.tool_name or ""
        arguments = decision.arguments or {}

        call: ToolCallRecord = self.context.record_tool_call(tool_name, arguments)

        tool = self.registry.get(tool_name)
        obs: Any = None
        if tool is None:
            obs = self.context.record_observation(
                call_id=call.call_id,
                tool_name=tool_name,
                success=False,
                error=f"unknown tool '{tool_name}'",
            )
        elif self.registry.is_mutating(tool_name) and self._confirm is not None:
            allowed = self._confirm(tool_name, arguments)
            if not allowed:
                obs = self.context.record_observation(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    success=False,
                    output={"tool_name": tool_name, "arguments": arguments},
                    error="mutation declined by user",
                )
        if obs is None:
            try:
                result = self.registry.execute(tool_name, self.client, arguments)
                obs = self.context.record_observation(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    success=result.ok,
                    output=result,
                    error=result.error,
                )
            except Exception as exc:  # noqa: BLE001
                obs = self.context.record_observation(
                    call_id=call.call_id,
                    tool_name=tool_name,
                    success=False,
                    error=str(exc),
                )

        if self._on_tool is not None:
            self._on_tool(call, obs)

    def run(self, task: str) -> AgentResult:
        """Execute the agent loop for ``task`` and return a terminal result."""
        self._reset_context(task)
        assert self.context is not None
        ctx = self.context

        declarations = self.registry.get_gemini_declarations()

        while True:
            self._check_deadline()
            ctx.bump_step()

            prompt_context = build_context(
                ctx, conversation_history=self._conversation_history
            )
            decision = self.provider.decide(  # type: ignore[attr-defined]
                ctx.goal, prompt_context, declarations
            )
            assert isinstance(decision, AgentDecision)

            if decision.type is AgentDecisionType.FINAL_RESPONSE:
                ctx.completed_at = self._now()
                return AgentResult(
                    ok=True, response=decision.response or "Task completed.",
                )

            if decision.type is AgentDecisionType.TOOL_CALL:
                self._dispatch(decision)
                continue

            if decision.type is AgentDecisionType.REQUEST_CLARIFICATION:
                ctx.completed_at = self._now()
                return AgentResult(
                    ok=False,
                    response=decision.response,
                    needs_clarification=True,
                )

            # FAIL / REQUEST_APPROVAL (approval is deferred to Phase 4 REPL).
            ctx.completed_at = self._now()
            return AgentResult(
                ok=False,
                error=decision.error_message
                or decision.response
                or "agent could not complete the task",
            )
