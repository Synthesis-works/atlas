import uuid
import enum
from sqlalchemy import String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from atlas_db.core.base import Base, BaseMixin, utcnow
from datetime import datetime

class ConfigurationScope(str, enum.Enum):
    ENV = "env"
    PROJECT = "project"
    BENCHMARK = "benchmark"

class Organization(Base, BaseMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    users: Mapped[list["User"]] = relationship("User", back_populates="organization", foreign_keys="User.org_id")
    projects: Mapped[list["Project"]] = relationship("Project", back_populates="organization", foreign_keys="Project.org_id")

class User(Base, BaseMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="users", foreign_keys=[org_id])

class Project(Base, BaseMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    organization: Mapped["Organization | None"] = relationship("Organization", back_populates="projects", foreign_keys=[org_id])

class Configuration(Base, BaseMixin):
    __tablename__ = "configurations"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[ConfigurationScope] = mapped_column(
        ENUM(ConfigurationScope, name="configuration_scope", create_type=False),
        nullable=False
    )
    
    versions: Mapped[list["ConfigurationVersion"]] = relationship("ConfigurationVersion", back_populates="configuration")

class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    configuration_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("configurations.id"), nullable=False)
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)
    
    # Simple mixin-like fields for versions that don't need full BaseMixin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    
    configuration: Mapped["Configuration"] = relationship("Configuration", back_populates="versions")
