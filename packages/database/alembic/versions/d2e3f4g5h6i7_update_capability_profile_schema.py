"""update capability profile schema

Revision ID: d2e3f4g5h6i7
Revises: c1d2e3f4g5h6
Create Date: 2026-07-21 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4g5h6i7"
down_revision: str | None = "c1d2e3f4g5h6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Drop unique constraint on atlas_run_id and rename column to execution_id
    if bind.engine.name == "sqlite":
        with op.batch_alter_table("capability_profiles") as batch_op:
            batch_op.drop_constraint("uq_capability_profiles_atlas_run_id", type_="unique")
            batch_op.alter_column("atlas_run_id", new_column_name="execution_id")

            # 2. Add new columns
            batch_op.add_column(sa.Column("evaluation_id", sa.Uuid(), nullable=True))
            batch_op.add_column(sa.Column("strategy_version_id", sa.Uuid(), nullable=True))
            batch_op.add_column(sa.Column("profile_version", sa.Integer(), nullable=True))

            # 3. Create foreign keys and indexes
            batch_op.create_foreign_key(
                None, "evaluation_results", ["evaluation_id"], ["id"], ondelete="CASCADE"
            )
            batch_op.create_foreign_key(
                None, "evaluation_strategy_versions", ["strategy_version_id"], ["id"]
            )

        op.create_index(
            op.f("ix_capability_profiles_evaluation_id"),
            "capability_profiles",
            ["evaluation_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_capability_profiles_execution_id"),
            "capability_profiles",
            ["execution_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_capability_profiles_strategy_version_id"),
            "capability_profiles",
            ["strategy_version_id"],
            unique=False,
        )
    else:
        op.drop_constraint(
            "uq_capability_profiles_atlas_run_id", "capability_profiles", type_="unique"
        )
        op.alter_column("capability_profiles", "atlas_run_id", new_column_name="execution_id")

        # 2. Add new columns
        op.add_column("capability_profiles", sa.Column("evaluation_id", sa.Uuid(), nullable=True))
        op.add_column(
            "capability_profiles", sa.Column("strategy_version_id", sa.Uuid(), nullable=True)
        )
        op.add_column(
            "capability_profiles", sa.Column("profile_version", sa.Integer(), nullable=True)
        )

        # 3. Create foreign keys and indexes
        op.create_foreign_key(
            None,
            "capability_profiles",
            "evaluation_results",
            ["evaluation_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            None,
            "capability_profiles",
            "evaluation_strategy_versions",
            ["strategy_version_id"],
            ["id"],
        )

        op.create_index(
            op.f("ix_capability_profiles_evaluation_id"),
            "capability_profiles",
            ["evaluation_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_capability_profiles_execution_id"),
            "capability_profiles",
            ["execution_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_capability_profiles_strategy_version_id"),
            "capability_profiles",
            ["strategy_version_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_capability_profiles_strategy_version_id"), table_name="capability_profiles"
    )
    op.drop_index(op.f("ix_capability_profiles_execution_id"), table_name="capability_profiles")
    op.drop_index(op.f("ix_capability_profiles_evaluation_id"), table_name="capability_profiles")

    op.drop_constraint(None, "capability_profiles", type_="foreignkey")
    op.drop_constraint(None, "capability_profiles", type_="foreignkey")

    op.drop_column("capability_profiles", "profile_version")
    op.drop_column("capability_profiles", "strategy_version_id")
    op.drop_column("capability_profiles", "evaluation_id")

    op.alter_column("capability_profiles", "execution_id", new_column_name="atlas_run_id")
    op.create_unique_constraint(
        "uq_capability_profiles_atlas_run_id", "capability_profiles", ["atlas_run_id"]
    )
