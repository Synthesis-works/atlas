"""add agent sessions table for P1 hosted conversational session API

Stores a bounded transcript per session, links to the current (or most recent)
AgentTaskRecord, and carries the JWT-derived ownership stamps so the API can
scope access without trusting the client.

Revision ID: add_agent_sessions
Revises: agent_api_ownership_and_throttle
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_agent_sessions"
down_revision: str | None = "agent_api_ownership_and_throttle"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "agent_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="gemini"),
        sa.Column("model", sa.String(length=255), nullable=True),
        sa.Column("current_task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "transcript",
            postgresql.JSONB,
            nullable=False,
            server_default="[]",
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_agent_sessions_created_by_user_id",
        "agent_sessions",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_sessions_organization_id",
        "agent_sessions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_agent_sessions_current_task_id",
        "agent_sessions",
        ["current_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agent_sessions_current_task_id", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_organization_id", table_name="agent_sessions")
    op.drop_index("ix_agent_sessions_created_by_user_id", table_name="agent_sessions")
    op.drop_table("agent_sessions")
