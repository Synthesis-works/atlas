"""Add ownership models

Revision ID: 8c0990ae707b
Revises: 4007056c9559
Create Date: 2026-07-15 21:39:09.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8c0990ae707b"
down_revision = "4007056c9559"
branch_labels = None
depends_on = None


def upgrade():
    # Enums
    organization_role = postgresql.ENUM(
        "OWNER", "ADMIN", "MEMBER", "VIEWER", name="organization_role", create_type=False
    )
    organization_role.create(op.get_bind(), checkfirst=True)

    membership_status = postgresql.ENUM(
        "ACTIVE", "PENDING", "SUSPENDED", "LEFT", name="membership_status", create_type=False
    )
    membership_status.create(op.get_bind(), checkfirst=True)

    invitation_status = postgresql.ENUM(
        "PENDING", "ACCEPTED", "EXPIRED", "REVOKED", name="invitation_status", create_type=False
    )
    invitation_status.create(op.get_bind(), checkfirst=True)

    # 1. Update organizations table
    op.add_column("organizations", sa.Column("slug", sa.String(length=255), nullable=True))
    op.add_column("organizations", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    # Note: For existing rows, you would typically populate the slug here before making it non-nullable.
    # For now, we alter it to nullable=False assuming no existing data or handling it in data migration.
    # We will assume this is a fresh schema or data migration will handle it.

    # 2. Update projects table
    op.add_column("projects", sa.Column("slug", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_projects_slug"), "projects", ["slug"], unique=False)
    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_unique_constraint("uq_project_org_name", ["org_id", "name"])

    # 3. Create organization_members table
    op.create_table(
        "organization_members",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("status", membership_status, server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_org_member"),
    )
    op.create_index(
        op.f("ix_organization_members_organization_id"),
        "organization_members",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_organization_members_user_id"), "organization_members", ["user_id"], unique=False
    )

    # 4. Add member tracking to projects
    op.add_column("projects", sa.Column("created_by_member_id", sa.UUID(), nullable=True))
    op.add_column("projects", sa.Column("updated_by_member_id", sa.UUID(), nullable=True))
    with op.batch_alter_table("projects") as batch_op:
        batch_op.create_foreign_key(
            "fk_projects_created_by_member",
            "organization_members",
            ["created_by_member_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_projects_updated_by_member",
            "organization_members",
            ["updated_by_member_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 5. Create invitations table
    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("status", invitation_status, server_default="PENDING", nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitations_email"), "invitations", ["email"], unique=False)
    op.create_index(
        op.f("ix_invitations_organization_id"), "invitations", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_invitations_token"), "invitations", ["token"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_invitations_token"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_organization_id"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_email"), table_name="invitations")
    op.drop_table("invitations")

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_constraint("fk_projects_updated_by_member", type_="foreignkey")
        batch_op.drop_constraint("fk_projects_created_by_member", type_="foreignkey")
    op.drop_column("projects", "updated_by_member_id")
    op.drop_column("projects", "created_by_member_id")

    op.drop_index(op.f("ix_organization_members_user_id"), table_name="organization_members")
    op.drop_index(
        op.f("ix_organization_members_organization_id"), table_name="organization_members"
    )
    op.drop_table("organization_members")

    op.drop_constraint("uq_project_org_name", "projects", type_="unique")
    op.drop_index(op.f("ix_projects_slug"), table_name="projects")
    op.drop_column("projects", "slug")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_column("organizations", "display_name")
    op.drop_column("organizations", "slug")

    postgresql.ENUM(name="invitation_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="membership_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="organization_role").drop(op.get_bind(), checkfirst=True)
