"""add agent task ownership and api usage counters

Part of P0 (Agent API security hardening). Adds the ownership identity for the
authenticated user that created each agent task (`created_by_user_id`,
`organization_id`), enabling owner-scoped reads/mutations and hiding the legacy
pre-P0 rows that carry NULL ownership. Also adds the `api_usage_counters` table
backing the opt-in DB-sliding-window per-user rate limits for the agent API.

Revision ID: agent_api_ownership_and_throttle
Revises: agent_task_execution_tracking
Create Date: 2026-09-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "agent_api_ownership_and_throttle"
down_revision: str | None = "agent_task_execution_tracking"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "agent_task_records",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agent_task_records",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_agent_task_records_created_by_user_id"),
        "agent_task_records",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_table(
        "api_usage_counters",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("window_until", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("api_usage_counters")
    op.drop_index(op.f("ix_agent_task_records_created_by_user_id"), table_name="agent_task_records")
    op.drop_column("agent_task_records", "organization_id")
    op.drop_column("agent_task_records", "created_by_user_id")
