"""Add password_hash and is_verified to user

Revision ID: 2d604cb686b3
Revises: e5842a639de0
Create Date: 2026-07-16 12:57:12.545529

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2d604cb686b3"
down_revision: str | Sequence[str] | None = "e5842a639de0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.add_column(
        "users", sa.Column("is_verified", sa.Boolean(), server_default="0", nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_verified")
    op.drop_column("users", "password_hash")
