"""GitHub Actions execution backend: metrics column + active-attempt idempotency

Revision ID: gha_execution_backend
Revises: add_benchmark_execution_attempts
Create Date: 2026-08-22

- benchmark_execution_attempts.metrics (JSONB): backend-specific observability
  payload (dispatch/queue/total latencies, GH run metadata).
- Partial unique index: at most ONE active attempt (PENDING / CONTAINER_CREATED
  / RUNNING) per execution. Enforces duplicate-dispatch protection and the
  retry/idempotency invariants at the database level.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "gha_execution_backend"
down_revision: str | Sequence[str] | None = "add_benchmark_execution_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_STATUSES = ("PENDING", "CONTAINER_CREATED", "RUNNING")


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "benchmark_execution_attempts",
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
    )
    op.create_index(
        "uq_active_attempt_per_execution",
        "benchmark_execution_attempts",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CONTAINER_CREATED', 'RUNNING')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_active_attempt_per_execution",
        table_name="benchmark_execution_attempts",
    )
    op.drop_column("benchmark_execution_attempts", "metrics")
