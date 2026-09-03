"""Client-side agent shared state & limits (Phase 1).

Mirrors the backend agent's ``AgentDecision``/``ToolCallRecord``/
``ObservationRecord`` shape (``apps/backend/agent/state.py``) but scoped to
the CLI agent loop.  The CLI agent never talks to the backend ``/agent/tasks``
loop; it drives its own loop over the deterministic SDK methods.  These models
carry that loop's per-run state and hard bounds.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

# ---- Hard runtime limits (tuned for a CLI one-shot REPL session) ----------
MAX_AGENT_STEPS = 20
MAX_AGENT_TOOL_CALLS = 40
AGENT_DEADLINE_SECONDS = 300.0  # 5 minutes wall-clock


class AgentLimitError(Exception):
    """Base class for loop-limit violations."""


class GoalExceededError(AgentLimitError):
    """The agent exceeded a hard step / tool-call bound."""


class AgentDecisionType(StrEnum):
    TOOL_CALL = "TOOL_CALL"
    FINAL_RESPONSE = "FINAL_RESPONSE"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    REQUEST_CLARIFICATION = "REQUEST_CLARIFICATION"
    FAIL = "FAIL"


class AgentDecision(BaseModel):
    """Structured next-action produced by the LLM provider."""

    type: AgentDecisionType
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    response: str | None = None
    error_message: str | None = None
    detail: str | None = None
    reasoning: str | None = None


class ToolCallRecord(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ObservationRecord(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentContext(BaseModel):
    """Mutable per-run state for a single CLI agent invocation.

    ``goal`` is the user's task; ``tool_calls``/``observations`` accumulate
    across the loop; counters drive the hard-limit checks.
    """

    goal: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    observations: list[ObservationRecord] = Field(default_factory=list)
    step_count: int = 0
    total_tool_calls: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def record_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> ToolCallRecord:
        if self.total_tool_calls + 1 > MAX_AGENT_TOOL_CALLS:
            raise GoalExceededError(f"tool-call limit ({MAX_AGENT_TOOL_CALLS}) exceeded")
        rec = ToolCallRecord(tool_name=tool_name, arguments=arguments)
        self.tool_calls.append(rec)
        self.total_tool_calls += 1
        return rec

    def record_observation(
        self,
        *,
        call_id: str,
        tool_name: str,
        success: bool,
        output: Any = None,
        error: str | None = None,
    ) -> ObservationRecord:
        rec = ObservationRecord(
            call_id=call_id, tool_name=tool_name, success=success, output=output, error=error
        )
        self.observations.append(rec)
        return rec

    def bump_step(self, by: int = 1) -> int:
        self.step_count += by
        if self.step_count > MAX_AGENT_STEPS:
            raise GoalExceededError(f"step limit ({MAX_AGENT_STEPS}) exceeded")
        return self.step_count
