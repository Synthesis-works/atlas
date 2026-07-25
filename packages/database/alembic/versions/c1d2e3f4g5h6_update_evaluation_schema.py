"""update evaluation schema

Revision ID: c1d2e3f4g5h6
Revises: b1c2d3e4f5g6
Create Date: 2026-07-21 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4g5h6"
down_revision: str | None = "b1c2d3e4f5g6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create evaluation_status Enum
    evaluation_status = postgresql.ENUM(
        "completed", "partial_success", "failed", name="evaluation_status"
    )
    evaluation_status.create(op.get_bind())

    # 2. Add columns to evaluation_results
    op.add_column(
        "evaluation_results",
        sa.Column("status", evaluation_status, nullable=False, server_default="completed"),
    )
    op.add_column(
        "evaluation_results",
        sa.Column("evaluation_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 3. Add column to capability_profiles
    op.add_column(
        "capability_profiles",
        sa.Column("score_explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # 4. Create evaluation_artifacts table
    op.create_table(
        "evaluation_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluation_result_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_uri", sa.String(length=1024), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_result_id"], ["evaluation_results.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_artifacts_evaluation_result_id"),
        "evaluation_artifacts",
        ["evaluation_result_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop evaluation_artifacts table
    op.drop_index(
        op.f("ix_evaluation_artifacts_evaluation_result_id"), table_name="evaluation_artifacts"
    )
    op.drop_table("evaluation_artifacts")

    # Drop column from capability_profiles
    op.drop_column("capability_profiles", "score_explanation")

    # Drop columns from evaluation_results
    op.drop_column("evaluation_results", "evaluation_context")
    op.drop_column("evaluation_results", "status")

    # Drop evaluation_status Enum
    evaluation_status = postgresql.ENUM(
        "completed", "partial_success", "failed", name="evaluation_status"
    )
    evaluation_status.drop(op.get_bind())
