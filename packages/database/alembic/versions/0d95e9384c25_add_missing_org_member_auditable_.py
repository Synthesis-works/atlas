"""add_missing_org_member_auditable_columns_and_execution_max_retries

Revision ID: 0d95e9384c25
Revises: 52ff82792e6a
Create Date: 2026-08-16 14:46:57.796228

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d95e9384c25'
down_revision: Union[str, Sequence[str], None] = '52ff82792e6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("organization_members", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("updated_by_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"))
        batch_op.create_foreign_key(
            "fk_organization_members_created_by_id_users",
            "users",
            ["created_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_organization_members_updated_by_id_users",
            "users",
            ["updated_by_id"],
            ["id"],
            ondelete="SET NULL",
        )
    
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.add_column(sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("executions", schema=None) as batch_op:
        batch_op.drop_column('max_retries')

    with op.batch_alter_table("organization_members", schema=None) as batch_op:
        batch_op.drop_constraint("fk_organization_members_updated_by_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_organization_members_created_by_id_users", type_="foreignkey")
        batch_op.drop_column("version_number")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("updated_by_id")
        batch_op.drop_column("created_by_id")
