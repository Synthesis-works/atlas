from datetime import datetime, timezone, UTC
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentTaskStatus(str, Enum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    REPAIRING = "REPAIRING"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AgentDecisionType(str, Enum):
    TOOL_CALL = "TOOL_CALL"
    FINAL_RESPONSE = "FINAL_RESPONSE"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    REPLAN = "REPLAN"
    FAIL = "FAIL"


class AgentPermission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    PUBLISH = "PUBLISH"


# Hard Safety & Runtime Bounds
MAX_STEPS = 25
MAX_TOOL_CALLS = 50
MAX_REPAIR_ATTEMPTS = 3
MAX_EXECUTION_TIME = 600  # seconds (10 minutes)
MAX_MODELS_PER_RUN = 5


class PlanStep(BaseModel):
    step_number: int
    description: str
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED, REPAIRED
    result_summary: Optional[str] = None


class ToolCallRecord(BaseModel):
    call_id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    arguments: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class ObservationRecord(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentDecision(BaseModel):
    type: AgentDecisionType
    tool_name: Optional[str] = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    response: Optional[str] = None
    plan_updates: Optional[list[PlanStep]] = None
    error_message: Optional[str] = None
    reasoning: Optional[str] = None


class TraceEvent(BaseModel):
    event_type: str
    details: dict[str, Any]
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class AgentTask(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    project_id: Optional[UUID] = None
    goal: str
    status: AgentTaskStatus = AgentTaskStatus.PENDING
    granted_permissions: list[AgentPermission] = Field(
        default_factory=lambda: [AgentPermission.READ, AgentPermission.WRITE, AgentPermission.EXECUTE]
    )
    
    # Progress & Memory State
    plan: list[PlanStep] = Field(default_factory=list)
    current_step: int = 0
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    observations: list[ObservationRecord] = Field(default_factory=list)
    execution_trace: list[TraceEvent] = Field(default_factory=list)
    
    # Limits and Counters
    step_count: int = 0
    total_tool_calls: int = 0
    repair_attempts: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Approval & Output State
    pending_tool_call: Optional[dict[str, Any]] = None
    approval_token: Optional[str] = None
    final_result: Optional[dict[str, Any]] = None
    error_detail: Optional[str] = None

    # Explicit Data Lineage & Resource Tracking
    benchmark_id: Optional[str] = None
    benchmark_version_id: Optional[str] = None
    dataset_id: Optional[str] = None
    dataset_version_id: Optional[str] = None
    execution_ids: list[str] = Field(default_factory=list)
    report_id: Optional[str] = None

    # Provider Telemetry
    primary_provider: str = "gemini"
    current_provider: str = "gemini"

    def record_trace(self, step: int, action: str, result: dict[str, Any]) -> None:
        self.add_trace(event_type=action, details={"step": step, **result})

    def add_trace(self, event_type: str, details: dict[str, Any]) -> None:
        self.execution_trace.append(TraceEvent(event_type=event_type, details=details))

    def is_active(self) -> bool:
        return self.status in {
            AgentTaskStatus.PENDING,
            AgentTaskStatus.PLANNING,
            AgentTaskStatus.EXECUTING,
            AgentTaskStatus.REPAIRING,
        }
