import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Table, Column, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import ENUM
from atlas_db.core.base import Base, BaseMixin, utcnow

class BenchmarkState(str, enum.Enum):
    PROPOSAL = "proposal"
    DESIGN = "design"
    DRAFT = "draft"
    VALIDATION = "validation"
    REVIEW = "review"
    PUBLISHED = "published"
    ARCHIVE = "archive"

# Association tables for Many-to-Many relationships
benchmark_category_link = Table(
    "benchmark_category_link",
    Base.metadata,
    Column("benchmark_id", ForeignKey("benchmarks.id"), primary_key=True),
    Column("category_id", ForeignKey("benchmark_categories.id"), primary_key=True)
)

benchmark_capability_link = Table(
    "benchmark_capability_link",
    Base.metadata,
    Column("benchmark_id", ForeignKey("benchmarks.id"), primary_key=True),
    Column("capability_id", ForeignKey("capabilities.id"), primary_key=True)
)

class BenchmarkCategory(Base, BaseMixin):
    __tablename__ = "benchmark_categories"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    benchmarks: Mapped[list["Benchmark"]] = relationship(
        "Benchmark", secondary=benchmark_category_link, back_populates="categories"
    )

class Capability(Base, BaseMixin):
    __tablename__ = "capabilities"

    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

    benchmarks: Mapped[list["Benchmark"]] = relationship(
        "Benchmark", secondary=benchmark_capability_link, back_populates="capabilities"
    )

class Benchmark(Base, BaseMixin):
    __tablename__ = "benchmarks"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    objective: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    visibility: Mapped[str | None] = mapped_column(String(50), nullable=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    categories: Mapped[list["BenchmarkCategory"]] = relationship(
        "BenchmarkCategory", secondary=benchmark_category_link, back_populates="benchmarks"
    )
    capabilities: Mapped[list["Capability"]] = relationship(
        "Capability", secondary=benchmark_capability_link, back_populates="benchmarks"
    )
    lifecycles: Mapped[list["BenchmarkLifecycle"]] = relationship("BenchmarkLifecycle", back_populates="benchmark")
    versions: Mapped[list["BenchmarkVersion"]] = relationship("BenchmarkVersion", back_populates="benchmark")

class BenchmarkLifecycle(Base):
    __tablename__ = "benchmark_lifecycles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[BenchmarkState] = mapped_column(
        ENUM(BenchmarkState, name="benchmark_state"),
        nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    benchmark: Mapped["Benchmark"] = relationship("Benchmark", back_populates="lifecycles")

class BenchmarkVersion(Base):
    __tablename__ = "benchmark_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    benchmark: Mapped["Benchmark"] = relationship("Benchmark", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("benchmark_id", "version_string", name="uq_benchmark_version"),
    )
