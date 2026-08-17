from __future__ import annotations
import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atlas_db.models.tasks import Task
    from atlas_db.models.core import Project

from atlas_db.core.base import Base, BaseMixin, utcnow
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class DatasetStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DatasetLifecycle(str, enum.Enum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALID = "valid"
    PUBLISHED = "published"
    FAILED = "failed"


class DatasetRegistry(Base, BaseMixin):
    __tablename__ = "dataset_registries"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    datasets: Mapped[list[Dataset]] = relationship("Dataset", back_populates="registry")


class DatasetSource(Base, BaseMixin):
    __tablename__ = "dataset_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    datasets: Mapped[list[Dataset]] = relationship("Dataset", back_populates="source")


class DatasetLicense(Base, BaseMixin):
    __tablename__ = "dataset_licenses"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)

    datasets: Mapped[list[Dataset]] = relationship("Dataset", back_populates="license")


class Dataset(Base, BaseMixin):
    __tablename__ = "datasets"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registry_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_registries.id"), nullable=True, index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_sources.id"), nullable=True, index=True
    )
    license_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_licenses.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    created_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[DatasetStatus] = mapped_column(
        ENUM(DatasetStatus, name="dataset_status"), nullable=False, default=DatasetStatus.ACTIVE
    )

    project: Mapped[Project] = relationship("Project")  # type: ignore
    registry: Mapped[DatasetRegistry | None] = relationship(
        "DatasetRegistry", back_populates="datasets"
    )
    source: Mapped[DatasetSource | None] = relationship("DatasetSource", back_populates="datasets")
    license: Mapped[DatasetLicense | None] = relationship(
        "DatasetLicense", back_populates="datasets"
    )
    versions: Mapped[list[DatasetVersion]] = relationship(
        "DatasetVersion", back_populates="dataset"
    )

    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_dataset_project_name"),)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lifecycle: Mapped[DatasetLifecycle] = mapped_column(
        ENUM(DatasetLifecycle, name="dataset_lifecycle"),
        nullable=False,
        default=DatasetLifecycle.UPLOADED,
    )
    schema_def: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    dataset: Mapped[Dataset] = relationship("Dataset", back_populates="versions")
    tasks: Mapped[list[Task]] = relationship("Task", back_populates="dataset_version")

    __mapper_args__ = {"version_id_col": version_number}

    __table_args__ = (UniqueConstraint("dataset_id", "version_string", name="uq_dataset_version"),)


class DatasetExportState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetExportAction(Base):
    __tablename__ = "dataset_export_actions"

    __table_args__ = (
        Index(
            "idx_unique_active_dataset_export",
            "dataset_version_id",
            unique=True,
            postgresql_where=text(
                "status IN ('PENDING'::dataset_export_state, 'RUNNING'::dataset_export_state)"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[DatasetExportState] = mapped_column(
        ENUM(DatasetExportState, name="dataset_export_state"),
        nullable=False,
        default=DatasetExportState.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
