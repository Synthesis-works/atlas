from atlas_db.repositories.base import BaseRepository
from atlas_db.models.core import Project
from atlas_db.models.authoring import Benchmark, BenchmarkVersion
from atlas_db.models.dataset import Dataset, DatasetVersion
from atlas_db.models.execution import ExecutionAdapter, EvaluationSession, AtlasRun
from atlas_db.models.evaluation import EvaluationStrategy, EvaluationResult
from atlas_db.models.reporting import Report, ReportVersion

class ProjectRepository(BaseRepository[Project]):
    def __init__(self):
        super().__init__(Project)

class BenchmarkRepository(BaseRepository[Benchmark]):
    def __init__(self):
        super().__init__(Benchmark)

class DatasetRepository(BaseRepository[Dataset]):
    def __init__(self):
        super().__init__(Dataset)

class EvaluationSessionRepository(BaseRepository[EvaluationSession]):
    def __init__(self):
        super().__init__(EvaluationSession)

class AtlasRunRepository(BaseRepository[AtlasRun]):
    def __init__(self):
        super().__init__(AtlasRun)

class EvaluationResultRepository(BaseRepository[EvaluationResult]):
    def __init__(self):
        super().__init__(EvaluationResult)

class ReportRepository(BaseRepository[Report]):
    def __init__(self):
        super().__init__(Report)

project_repo = ProjectRepository()
benchmark_repo = BenchmarkRepository()
dataset_repo = DatasetRepository()
session_repo = EvaluationSessionRepository()
run_repo = AtlasRunRepository()
result_repo = EvaluationResultRepository()
report_repo = ReportRepository()
