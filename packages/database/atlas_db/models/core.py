import enum
import uuid
from datetime import datetime

from atlas_db.core.base import Base, BaseMixin, utcnow
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship


class ConfigurationScope(str, enum.Enum):
    ENV = "env"
    PROJECT = "project"
    BENCHMARK = "benchmark"


class OrganizationRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    LEFT = "left"


class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Organization(Base, BaseMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(
        "User", back_populates="organization", foreign_keys="User.org_id"
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="organization", foreign_keys="Project.org_id"
    )
    members: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMember.organization_id",
    )
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation",
        back_populates="organization",
        cascade="all, delete-orphan",
        foreign_keys="Invitation.organization_id",
    )


class User(Base, BaseMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="users", foreign_keys=[org_id]
    )
    memberships: Mapped[list["OrganizationMember"]] = relationship(
        "OrganizationMember",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="OrganizationMember.user_id",
    )


class OrganizationMember(Base, BaseMixin):
    __tablename__ = "organization_members"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[OrganizationRole] = mapped_column(
        ENUM(OrganizationRole, name="organization_role"), nullable=False
    )
    status: Mapped[MembershipStatus] = mapped_column(
        ENUM(MembershipStatus, name="membership_status"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="memberships", foreign_keys=[user_id]
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="members", foreign_keys=[organization_id]
    )

    __table_args__ = (UniqueConstraint("user_id", "organization_id", name="uq_org_member"),)


class Invitation(Base, BaseMixin):
    __tablename__ = "invitations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[OrganizationRole] = mapped_column(
        ENUM(OrganizationRole, name="organization_role_invitation", create_type=False),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[InvitationStatus] = mapped_column(
        ENUM(InvitationStatus, name="invitation_status"),
        nullable=False,
        default=InvitationStatus.PENDING,
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="invitations", foreign_keys=[organization_id]
    )


class Project(Base, BaseMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)
    created_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_member_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organization_members.id", ondelete="SET NULL"), nullable=True
    )

    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="projects", foreign_keys=[org_id]
    )

    __table_args__ = (UniqueConstraint("org_id", "name", name="uq_project_org_name"),)


class Configuration(Base, BaseMixin):
    __tablename__ = "configurations"

    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[ConfigurationScope] = mapped_column(
        ENUM(ConfigurationScope, name="configuration_scope"), nullable=False
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    benchmark_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"), nullable=True, index=True
    )

    __table_args__ = (
        CheckConstraint(
            "(scope = 'PROJECT' AND project_id IS NOT NULL AND benchmark_id IS NULL) OR "
            "(scope = 'BENCHMARK' AND benchmark_id IS NOT NULL AND project_id IS NULL) OR "
            "(scope = 'ENV' AND project_id IS NULL AND benchmark_id IS NULL)",
            name="chk_configuration_scope",
        ),
    )

    versions: Mapped[list["ConfigurationVersion"]] = relationship(
        "ConfigurationVersion", back_populates="configuration"
    )


class ConfigurationVersion(Base):
    __tablename__ = "configuration_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    configuration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("configurations.id"), nullable=False, index=True
    )
    version_string: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[dict | list | None] = mapped_column(JSONB, nullable=True)

    # Simple mixin-like fields for versions that don't need full BaseMixin
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    configuration: Mapped["Configuration"] = relationship(
        "Configuration", back_populates="versions"
    )

    __table_args__ = (
        UniqueConstraint("configuration_id", "version_string", name="uq_configuration_version"),
    )
