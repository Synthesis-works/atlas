"""make_datasets_project_scoped

Revision ID: a5eef4ee78a5
Revises: 2d604cb686b3
Create Date: 2026-07-16 16:17:35.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a5eef4ee78a5"
down_revision: str | None = "2d604cb686b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column("created_by_member_id", sa.UUID(), nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(), nullable=True, server_default="ACTIVE")
        )
        batch_op.create_foreign_key(
            "fk_datasets_project_id_projects", "projects", ["project_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_datasets_created_by_member_id_org_members",
            "organization_members",
            ["created_by_member_id"],
            ["id"],
        )
        batch_op.create_index("ix_datasets_project_id", ["project_id"])


def downgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_index("ix_datasets_project_id")
        batch_op.drop_constraint("fk_datasets_project_id_projects", type_="foreignkey")
        batch_op.drop_constraint("fk_datasets_created_by_member_id_org_members", type_="foreignkey")
        batch_op.drop_column("status")
        batch_op.drop_column("created_by_member_id")
        batch_op.drop_column("project_id")
