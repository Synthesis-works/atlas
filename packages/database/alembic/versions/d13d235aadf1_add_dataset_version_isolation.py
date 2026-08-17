"""add_dataset_version_isolation

Revision ID: d13d235aadf1
Revises: 
Create Date: 2026-08-15 14:30:32.022178

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd13d235aadf1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dataset_version_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_executions_dataset_version_id'), ['dataset_version_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_executions_dataset_version_id_dataset_versions'), 'dataset_versions', ['dataset_version_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('test_cases', schema=None) as batch_op:
        batch_op.add_column(sa.Column('dataset_version_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_test_cases_dataset_version_id'), ['dataset_version_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_test_cases_dataset_version_id_dataset_versions'), 'dataset_versions', ['dataset_version_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('test_cases', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_test_cases_dataset_version_id_dataset_versions'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_test_cases_dataset_version_id'))
        batch_op.drop_column('dataset_version_id')

    with op.batch_alter_table('executions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_executions_dataset_version_id_dataset_versions'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_executions_dataset_version_id'))
        batch_op.drop_column('dataset_version_id')
