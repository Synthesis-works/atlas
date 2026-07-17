import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from atlas_db.models.authoring import Benchmark, BenchmarkVersion, BenchmarkState
from apps.backend.schemas.benchmarks import BenchmarkCreate, BenchmarkVersionCreate

class BenchmarkService:
    def __init__(self, db: Session):
        self.db = db

    def list_benchmarks(self, project_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[Benchmark]:
        """List all non-archived benchmarks for a given project."""
        stmt = (
            select(Benchmark)
            .where(
                Benchmark.project_id == project_id,
                Benchmark.status != BenchmarkState.ARCHIVE
            )
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def get_benchmark(self, benchmark_id: uuid.UUID) -> Optional[Benchmark]:
        """Get a benchmark by its ID, unless it is archived."""
        stmt = select(Benchmark).where(
            Benchmark.id == benchmark_id,
            Benchmark.status != BenchmarkState.ARCHIVE
        )
        return self.db.scalars(stmt).first()

    def create_benchmark(self, project_id: uuid.UUID, member_id: uuid.UUID, data: BenchmarkCreate) -> Benchmark:
        """Create a new benchmark along with its initial version."""
        new_benchmark = Benchmark(
            project_id=project_id,
            name=data.name,
            objective=data.objective,
            difficulty=data.difficulty,
            domain=data.domain,
            type=data.type,
            visibility=data.visibility,
            author_id=member_id,
            status=BenchmarkState.DRAFT  # Or PROPOSAL, but let's start with DRAFT
        )
        self.db.add(new_benchmark)
        self.db.flush()  # To get new_benchmark.id

        # Create initial version
        self._create_version(new_benchmark.id, member_id, data.initial_version)

        self.db.commit()
        self.db.refresh(new_benchmark)
        return new_benchmark

    def create_benchmark_version(self, benchmark_id: uuid.UUID, member_id: uuid.UUID, data: BenchmarkVersionCreate) -> BenchmarkVersion:
        """Append a new, immutable version to an existing benchmark."""
        benchmark = self.get_benchmark(benchmark_id)
        if not benchmark:
            raise ValueError("Benchmark not found or is archived.")

        new_version = self._create_version(benchmark_id, member_id, data)
        self.db.commit()
        self.db.refresh(new_version)
        return new_version

    def _create_version(self, benchmark_id: uuid.UUID, member_id: uuid.UUID, data: BenchmarkVersionCreate) -> BenchmarkVersion:
        new_version = BenchmarkVersion(
            benchmark_id=benchmark_id,
            version_string=data.version_string,
            primary_dataset_version_id=data.primary_dataset_version_id,
            evaluation_config=data.evaluation_config,
            metric_config=data.metric_config,
            scoring_policy=data.scoring_policy,
            created_by_id=member_id
        )
        self.db.add(new_version)
        return new_version
