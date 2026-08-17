"""d1_5_lossless

Revision ID: b8fe9ea13c79
Revises: 0fe98ac3f9d1
Create Date: 2026-08-13 22:49:56.750612

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8fe9ea13c79'
down_revision: str | Sequence[str] | None = '0fe98ac3f9d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add metadata to tasks
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False)
        )

    # 2. Add context_setup and is_challenge to evaluation_rules
    with op.batch_alter_table('evaluation_rules', schema=None) as batch_op:
        batch_op.add_column(sa.Column('context_setup', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('is_challenge', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('evaluation_rules', schema=None) as batch_op:
        batch_op.drop_column('is_challenge')
        batch_op.drop_column('context_setup')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('metadata')
