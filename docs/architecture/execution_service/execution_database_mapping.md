# Execution Database Mapping

To support the Execution Service state machine and lifecycle, the existing `packages/database/atlas_db/models/execution.py` requires structural enhancements.

## 1. Expanding `RunStatus`
We will expand the current enum to match the refined state machine, adding `VALIDATING` and other required states:
```python
class RunStatus(str, enum.Enum):
    CREATED = "created"
    VALIDATING = "validating"
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
```

## 2. Enhancing `AtlasRun`
We need to track heartbeats, errors, and configuration to support fault tolerance and the Scheduler.
```python
# Added to AtlasRun
last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
error_message: Mapped[str | None] = mapped_column(String, nullable=True)
config: Mapped[dict | None] = mapped_column(JSONB, nullable=True) # stores max_retries, fail_fast, priority
```

## 3. Introducing `AtlasTask`
An intermediate entity to track the *execution attempt* of a test case, enabling granular retry logic without muddying the final `ModelOutput`.

```python
class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

class AtlasTask(Base, BaseMixin):
    __tablename__ = "atlas_tasks"

    atlas_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atlas_runs.id", ondelete="CASCADE"), index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), index=True)
    
    status: Mapped[TaskStatus] = mapped_column(ENUM(TaskStatus, name="task_status"), default=TaskStatus.QUEUED)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    
    run: Mapped["AtlasRun"] = relationship("AtlasRun", back_populates="tasks")
```

## 4. `ModelOutput` Relationship
`ModelOutput` will now link to `AtlasTask` (1-to-1) in addition to `AtlasRun`. When a task succeeds, it writes its final `ModelOutput`.

## 5. Artifact and Logs
The existing `Artifact` table is sufficient for tracking files and weights.
