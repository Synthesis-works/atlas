"""add benchmark dataset relationships and configs

Revision ID: 1df343a1dca3
Revises: a5eef4ee78a5
Create Date: 2026-07-17 12:18:57.008316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1df343a1dca3'
down_revision: Union[str, Sequence[str], None] = 'a5eef4ee78a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table('benchmark_versions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('primary_dataset_version_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('evaluation_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column('metric_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        batch_op.add_column(sa.Column('scoring_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
        batch_op.create_index(batch_op.f('ix_benchmark_versions_primary_dataset_version_id'), ['primary_dataset_version_id'], unique=False)
        batch_op.create_foreign_key(batch_op.f('fk_benchmark_versions_primary_dataset_version_id_dataset_versions'), 'dataset_versions', ['primary_dataset_version_id'], ['id'], ondelete='RESTRICT')

def downgrade() -> None:
    with op.batch_alter_table('benchmark_versions', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_benchmark_versions_primary_dataset_version_id_dataset_versions'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_benchmark_versions_primary_dataset_version_id'))
        batch_op.drop_column('scoring_policy')
        batch_op.drop_column('metric_config')
        batch_op.drop_column('evaluation_config')
        batch_op.drop_column('primary_dataset_version_id')
