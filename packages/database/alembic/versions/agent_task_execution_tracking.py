"""add agent task celery execution tracking

Adds optional `instance_id` and `heartbeat_at` columns to `agent_task_records`
so a durable worker (or a serverless instance) can claim ownership of an
in-flight agent task and prove liveness. Reads and mutations can then safely
operate against the persisted store across processes instead of one
instance-local in-memory dict, and stale-owner recovery can distinguish a live
loop from a frozen one.

Revision ID: agent_task_execution_tracking
Revises: add_execution_idempotency_key
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "agent_task_execution_tracking"
down_revision: str | None = "add_execution_idempotency_key"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "agent_task_records",
        sa.Column("instance_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "agent_task_records",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_task_records", "heartbeat_at")
    op.drop_column("agent_task_records", "instance_id")
