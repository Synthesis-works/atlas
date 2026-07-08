import uuid
import enum
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from atlas_db.core.base import Base, BaseMixin, utcnow

class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    FAILED = "failed"

class DatasetRegistry(Base, BaseMixin):
    __tablename__ = "dataset_registries"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="registry")

class DatasetSource(Base, BaseMixin):
    __tablename__ = "dataset_sources"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="source")

class DatasetLicense(Base, BaseMixin):
    __tablename__ = "dataset_licenses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String, nullable=True)

    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="license")

class Dataset(Base, BaseMixin):
    __tablename__ = "datasets"

    registry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_registries.id"), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_sources.id"), nullable=False, index=True)
    license_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dataset_licenses.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    registry: Mapped["DatasetRegistry"] = relationship("DatasetRegistry", back_populates="datasets")
    source: Mapped["DatasetSource"] = relationship("DatasetSource", back_populates="datasets")
    license: Mapped["DatasetLicense"] = relationship("DatasetLicense", back_populates="datasets")
    versions: Mapped[list["DatasetVersion"]] = relationship("DatasetVersion", back_populates="dataset")

class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.id"), nullable=False, index=True)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(
        ENUM(ValidationStatus, name="dataset_validation_status"),
        nullable=False,
        default=ValidationStatus.PENDING
    )
    schema_def: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="versions")

    __mapper_args__ = {"version_id_col": version_number}
