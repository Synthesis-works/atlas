"""Add execution progress and queued_at

Revision ID: 7b06ff45e6cd
Revises: e837053abeb8
Create Date: 2026-07-17 13:52:32.507184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7b06ff45e6cd'
down_revision: Union[str, Sequence[str], None] = 'e837053abeb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_items', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('completed_items', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.drop_column('queued_at')
        batch_op.drop_column('completed_items')
        batch_op.drop_column('total_items')
