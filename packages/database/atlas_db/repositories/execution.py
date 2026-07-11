from sqlalchemy.orm import Session
from .base import BaseRepository
from atlas_db.models.execution import ExecutionAdapter, ExecutionAdapterVersion, EvaluationSession, AtlasRun, ModelOutput, Artifact

class ExecutionAdapterRepository(BaseRepository[ExecutionAdapter]):
    model = ExecutionAdapter

class ExecutionAdapterVersionRepository(BaseRepository[ExecutionAdapterVersion]):
    model = ExecutionAdapterVersion

class EvaluationSessionRepository(BaseRepository[EvaluationSession]):
    model = EvaluationSession

class AtlasRunRepository(BaseRepository[AtlasRun]):
    model = AtlasRun

class ModelOutputRepository(BaseRepository[ModelOutput]):
    model = ModelOutput

class ArtifactRepository(BaseRepository[Artifact]):
    model = Artifact
