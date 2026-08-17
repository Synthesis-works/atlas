"""add max_retries to executions

Revision ID: 9ad2cfc0f0fc
Revises: 52ff82792e6a
Create Date: 2026-08-17 11:15:16.782179

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9ad2cfc0f0fc"
down_revision: str | Sequence[str] | None = "52ff82792e6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3")
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column("max_retries")
