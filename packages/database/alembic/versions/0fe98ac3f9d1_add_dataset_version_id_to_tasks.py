"""add dataset_version_id to tasks

Revision ID: 0fe98ac3f9d1
Revises: 52ff82792e6a
Create Date: 2026-08-13 22:11:52.076859

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0fe98ac3f9d1"
down_revision: str | Sequence[str] | None = "52ff82792e6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.alter_column(
            "benchmark_version_id", existing_type=sa.CHAR(length=32), nullable=True
        )
        batch_op.add_column(sa.Column("dataset_version_id", sa.Uuid(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_tasks_dataset_version_id"), ["dataset_version_id"], unique=False
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_tasks_dataset_version_id_dataset_versions"),
            "dataset_versions",
            ["dataset_version_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            "task_version_check",
            "benchmark_version_id IS NOT NULL OR dataset_version_id IS NOT NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_constraint("task_version_check", type_="check")
        batch_op.drop_constraint(
            batch_op.f("fk_tasks_dataset_version_id_dataset_versions"), type_="foreignkey"
        )
        batch_op.drop_index(batch_op.f("ix_tasks_dataset_version_id"))
        batch_op.drop_column("dataset_version_id")
        batch_op.alter_column(
            "benchmark_version_id", existing_type=sa.CHAR(length=32), nullable=False
        )
