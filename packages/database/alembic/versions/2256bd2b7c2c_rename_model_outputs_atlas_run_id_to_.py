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
    # Create dummy atlas_runs table so SQLAlchemy reflection doesn't fail on the dangling FK
    op.create_table("atlas_runs", sa.Column("id", sa.Uuid(), primary_key=True))
    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.drop_index("ix_model_outputs_atlas_run_id")
        batch_op.drop_constraint("fk_model_outputs_atlas_run_id_atlas_runs", type_="foreignkey")
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
    op.drop_table("atlas_runs")


def downgrade() -> None:
    op.create_table("executions", sa.Column("id", sa.Uuid(), primary_key=True))
    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.drop_index("ix_model_outputs_execution_id")
        batch_op.drop_constraint("fk_model_outputs_execution_id_executions", type_="foreignkey")
        batch_op.alter_column("execution_id", new_column_name="atlas_run_id")
        batch_op.create_foreign_key(
            "fk_model_outputs_atlas_run_id_atlas_runs",
            "atlas_runs",
            ["atlas_run_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("model_outputs", schema=None) as batch_op:
        batch_op.create_index("ix_model_outputs_atlas_run_id", ["atlas_run_id"])
    op.drop_table("executions")
