"""add_basemixin_to_evaluation_artifacts

Revision ID: 52ff82792e6a
Revises: 2256bd2b7c2c
Create Date: 2026-07-22 21:59:52.482705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52ff82792e6a'
down_revision: Union[str, Sequence[str], None] = '2256bd2b7c2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite workaround: batch_alter_table reflects all tables and fails on missing atlas_runs
    op.execute("CREATE TABLE IF NOT EXISTS atlas_runs (id CHAR(32) PRIMARY KEY)")
    
    with op.batch_alter_table('evaluation_artifacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('updated_by_id', sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'))
        batch_op.create_foreign_key('fk_evaluation_artifacts_created_by_id_users', 'users', ['created_by_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_evaluation_artifacts_updated_by_id_users', 'users', ['updated_by_id'], ['id'], ondelete='SET NULL')

    op.execute("DROP TABLE atlas_runs")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("CREATE TABLE IF NOT EXISTS atlas_runs (id CHAR(32) PRIMARY KEY)")
    with op.batch_alter_table('evaluation_artifacts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_evaluation_artifacts_updated_by_id_users', type_='foreignkey')
        batch_op.drop_constraint('fk_evaluation_artifacts_created_by_id_users', type_='foreignkey')
        batch_op.drop_column('version_number')
        batch_op.drop_column('archived_at')
        batch_op.drop_column('updated_by_id')
        batch_op.drop_column('created_by_id')
    op.execute("DROP TABLE atlas_runs")
