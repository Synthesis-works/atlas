"""merge multiple heads

Revision ID: e5842a639de0
Revises: 27624aa4c089, 8c0990ae707b
Create Date: 2026-07-16 12:55:01.115709

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5842a639de0'
down_revision: Union[str, Sequence[str], None] = ('27624aa4c089', '8c0990ae707b')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
