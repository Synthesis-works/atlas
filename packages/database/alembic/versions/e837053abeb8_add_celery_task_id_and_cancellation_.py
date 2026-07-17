"""Add celery_task_id and cancellation_requested to Execution

Revision ID: e837053abeb8
Revises: 3a1cf533642c
Create Date: 2026-07-17 13:33:24.181483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e837053abeb8'
down_revision: Union[str, Sequence[str], None] = '3a1cf533642c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('celery_task_id', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('cancellation_requested', sa.Boolean(), server_default='false', nullable=False))
        batch_op.create_index(batch_op.f('ix_executions_celery_task_id'), ['celery_task_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_executions_celery_task_id'))
        batch_op.drop_column('cancellation_requested')
        batch_op.drop_column('celery_task_id')
