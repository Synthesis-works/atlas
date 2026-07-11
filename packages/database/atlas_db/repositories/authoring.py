from sqlalchemy.orm import Session
from .base import BaseRepository
from atlas_db.models.authoring import Benchmark, BenchmarkVersion, BenchmarkLifecycle, BenchmarkCategory, Capability

class BenchmarkRepository(BaseRepository[Benchmark]):
    model = Benchmark

class BenchmarkVersionRepository(BaseRepository[BenchmarkVersion]):
    model = BenchmarkVersion

class BenchmarkLifecycleRepository(BaseRepository[BenchmarkLifecycle]):
    model = BenchmarkLifecycle

class BenchmarkCategoryRepository(BaseRepository[BenchmarkCategory]):
    model = BenchmarkCategory

class CapabilityRepository(BaseRepository[Capability]):
    model = Capability
