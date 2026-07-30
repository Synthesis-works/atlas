"""rename_model_outputs_atlas_run_id_to_execution_id

Revision ID: 2256bd2b7c2c
Revises: f1f2f3f4f5f6
Create Date: 2026-07-22 21:46:02.095207

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.

revision: str = "2256bd2b7c2c"
down_revision: str | Sequence[str] | None = "f1f2f3f4f5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # [HISTORICAL MIGRATION REWRITE - Dockerization Fix]
    # Removed the creation of a dummy `atlas_runs` table and the redundant
    # `drop_constraint` call. The dangling foreign key constraint was properly
    # dropped in the earlier `3a1cf533642c_execution_models.py` migration to
    # prevent Postgres from crashing when `atlas_runs` was dropped.

    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.drop_index("ix_model_outputs_atlas_run_id")
        batch_op.alter_column("atlas_run_id", new_column_name="execution_id")
        batch_op.create_foreign_key(
            "fk_model_outputs_execution_id_executions",
            "executions",
            ["execution_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.create_index("ix_model_outputs_execution_id", ["execution_id"])


def downgrade() -> None:
    # [HISTORICAL MIGRATION REWRITE - Dockerization Fix]
    # Removed the creation of a dummy `executions` table and the redundant
    # `drop_constraint` call. The dangling foreign key constraint will be recreated
    # in the earlier `3a1cf533642c_execution_models.py` migration.

    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.drop_index("ix_model_outputs_execution_id")
        batch_op.alter_column("execution_id", new_column_name="atlas_run_id")

    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.create_index("ix_model_outputs_atlas_run_id", ["atlas_run_id"])
