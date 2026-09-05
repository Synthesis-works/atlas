"""add execution idempotency key

Adds an optional `idempotency_key` to `executions` with a partial unique index
so repeated or concurrently replayed dispatch requests resolve to a single
execution record instead of creating duplicates.

Revision ID: add_execution_idempotency_key
Revises: gha_execution_backend
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "add_execution_idempotency_key"
down_revision: str | None = "gha_execution_backend"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "executions",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_executions_idempotency_key",
        "executions",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_executions_idempotency_key", table_name="executions")
    op.drop_column("executions", "idempotency_key")
