from .base import BaseRepository
from atlas_db.models.execution import ExecutionAdapter, ExecutionAdapterVersion, Execution, ModelOutput, Artifact

class ExecutionAdapterRepository(BaseRepository[ExecutionAdapter]):
    model = ExecutionAdapter

class ExecutionAdapterVersionRepository(BaseRepository[ExecutionAdapterVersion]):
    model = ExecutionAdapterVersion

class ExecutionRepository(BaseRepository[Execution]):
    model = Execution


class ModelOutputRepository(BaseRepository[ModelOutput]):
    model = ModelOutput

class ArtifactRepository(BaseRepository[Artifact]):
    model = Artifact
