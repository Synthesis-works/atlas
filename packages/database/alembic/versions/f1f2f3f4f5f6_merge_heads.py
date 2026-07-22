"""merge all heads

Revision ID: f1f2f3f4f5f6
Revises: 7b06ff45e6cd, d2e3f4g5h6i7, 375aa9bc04ec
Create Date: 2026-07-22 15:00:00.000000

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "f1f2f3f4f5f6"
down_revision: str | Sequence[str] | None = ("7b06ff45e6cd", "d2e3f4g5h6i7", "375aa9bc04ec")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
