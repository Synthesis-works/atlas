from dataclasses import dataclass
from datetime import datetime
import uuid
from typing import Optional

@dataclass(frozen=True)
class EvaluationStartedEvent:
    evaluation_id: uuid.UUID
    execution_id: uuid.UUID
    strategy_version_id: uuid.UUID
    timestamp: datetime

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def event_version(self) -> int:
        return 1

    def to_dict(self) -> dict:
        import dataclasses
        data = dataclasses.asdict(self)
        def _serialize_val(val):
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, dict):
                return {k: _serialize_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_serialize_val(v) for v in val]
            return val
        return {k: _serialize_val(v) for k, v in data.items() if k != "timestamp"}

@dataclass(frozen=True)
class EvaluationCompletedEvent:
    evaluation_id: uuid.UUID
    execution_id: uuid.UUID
    overall_score: Optional[float]
    duration_ms: int
    artifact_count: int
    timestamp: datetime

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def event_version(self) -> int:
        return 1

    def to_dict(self) -> dict:
        import dataclasses
        data = dataclasses.asdict(self)
        def _serialize_val(val):
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, dict):
                return {k: _serialize_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_serialize_val(v) for v in val]
            return val
        return {k: _serialize_val(v) for k, v in data.items() if k != "timestamp"}

@dataclass(frozen=True)
class EvaluationFailedEvent:
    evaluation_id: uuid.UUID
    execution_id: uuid.UUID
    retryable: bool
    reason: str
    timestamp: datetime

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    @property
    def event_version(self) -> int:
        return 1

    def to_dict(self) -> dict:
        import dataclasses
        data = dataclasses.asdict(self)
        def _serialize_val(val):
            if isinstance(val, uuid.UUID):
                return str(val)
            if isinstance(val, datetime):
                return val.isoformat()
            if isinstance(val, dict):
                return {k: _serialize_val(v) for k, v in val.items()}
            if isinstance(val, list):
                return [_serialize_val(v) for v in val]
            return val
        return {k: _serialize_val(v) for k, v in data.items() if k != "timestamp"}
