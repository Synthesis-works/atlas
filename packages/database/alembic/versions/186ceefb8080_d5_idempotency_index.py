"""d5_idempotency_index

Revision ID: 186ceefb8080
Revises: 7965b85752ad
Create Date: 2026-08-15 15:00:06.958958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '186ceefb8080'
down_revision: Union[str, Sequence[str], None] = '7965b85752ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    import sqlalchemy as sa
    
    # Check for duplicates before creating the index
    result = bind.execute(sa.text('''
        SELECT dataset_version_id, count(id)
        FROM dataset_export_actions
        WHERE status IN ('PENDING', 'RUNNING')
        GROUP BY dataset_version_id
        HAVING count(id) > 1
    ''')).fetchall()
    
    if result:
        raise Exception(f"D5 Preflight blocked: Duplicate active exports exist constraints cannot be applied. Duplicates: {result}")

    # No duplicates, safe to create the partial unique index
    op.create_index(
        'idx_unique_active_dataset_export',
        'dataset_export_actions',
        ['dataset_version_id'],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'idx_unique_active_dataset_export',
        table_name='dataset_export_actions'
    )
