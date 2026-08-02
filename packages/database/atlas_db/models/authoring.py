import enum
import uuid
from datetime import datetime

from atlas_db.core.base import Base, BaseMixin, utcnow
from sqlalchemy import Column, DateTime, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
    Column("category_id", ForeignKey("benchmark_categories.id"), primary_key=True),
)

benchmark_capability_link = Table(
    "benchmark_capability_link",
    Base.metadata,
    Column("benchmark_id", ForeignKey("benchmarks.id"), primary_key=True),
    Column("capability_id", ForeignKey("capabilities.id"), primary_key=True),
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

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    objective: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    visibility: Mapped[str | None] = mapped_column(String(50), nullable=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    categories: Mapped[list["BenchmarkCategory"]] = relationship(
        "BenchmarkCategory", secondary=benchmark_category_link, back_populates="benchmarks"
    )
    capabilities: Mapped[list["Capability"]] = relationship(
        "Capability", secondary=benchmark_capability_link, back_populates="benchmarks"
    )
    lifecycles: Mapped[list["BenchmarkLifecycle"]] = relationship(
        "BenchmarkLifecycle", back_populates="benchmark"
    )
    versions: Mapped[list["BenchmarkVersion"]] = relationship(
        "BenchmarkVersion", back_populates="benchmark"
    )


class BenchmarkLifecycle(Base):
    __tablename__ = "benchmark_lifecycles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    state: Mapped[BenchmarkState] = mapped_column(
        ENUM(BenchmarkState, name="benchmark_state"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    benchmark: Mapped["Benchmark"] = relationship("Benchmark", back_populates="lifecycles")


benchmark_version_dataset_link = Table(
    "benchmark_version_dataset_link",
    Base.metadata,
    Column(
        "benchmark_version_id",
        ForeignKey("benchmark_versions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dataset_version_id",
        ForeignKey("dataset_versions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class BenchmarkVersion(Base):
    __tablename__ = "benchmark_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=False
    )
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)

    primary_dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    evaluation_config: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    metric_config: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    scoring_policy: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    # Version Metadata
    evaluation_strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        postgresql.UUID(as_uuid=True), nullable=True
    )

    benchmark: Mapped["Benchmark"] = relationship("Benchmark", back_populates="versions")
    dataset_versions: Mapped[list["DatasetVersion"]] = relationship(  # type: ignore
        "DatasetVersion", secondary=benchmark_version_dataset_link
    )
    primary_dataset_version: Mapped["DatasetVersion | None"] = relationship("DatasetVersion")  # type: ignore

    __table_args__ = (
        UniqueConstraint("benchmark_id", "version_string", name="uq_benchmark_version"),
    )
