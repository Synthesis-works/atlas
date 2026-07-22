"""implement_readiness_review

Revision ID: 27624aa4c089
Revises: 4007056c9559
Create Date: 2026-07-11 17:56:39.664254

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "27624aa4c089"
down_revision: str | Sequence[str] | None = "4007056c9559"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. New Indexes
    op.create_index(
        "ix_atlas_runs_status_created_at",
        "atlas_runs",
        ["status", "created_at"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_atlas_runs_target_model", "atlas_runs", ["target_model"], if_not_exists=True
    )
    op.create_index("ix_benchmarks_status", "benchmarks", ["status"], if_not_exists=True)
    op.create_index("ix_benchmarks_name", "benchmarks", ["name"], if_not_exists=True)
    op.create_index("ix_datasets_name", "datasets", ["name"], if_not_exists=True)

    # 2. Unique Constraints
    with op.batch_alter_table("configuration_versions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_configuration_version", ["configuration_id", "version_string"]
        )
    with op.batch_alter_table("benchmark_versions") as batch_op:
        batch_op.create_unique_constraint(
            "uq_benchmark_version", ["benchmark_id", "version_string"]
        )
    with op.batch_alter_table("dataset_versions") as batch_op:
        batch_op.create_unique_constraint("uq_dataset_version", ["dataset_id", "version_string"])
    with op.batch_alter_table("execution_adapter_versions") as batch_op:
        batch_op.create_unique_constraint("uq_adapter_version", ["adapter_id", "version_string"])
    with op.batch_alter_table("evaluation_strategy_versions") as batch_op:
        batch_op.create_unique_constraint("uq_strategy_version", ["strategy_id", "version_string"])

    # 3. Cascade Delete (Drop Restrict, Add Cascade)
    with op.batch_alter_table("benchmark_lifecycles") as batch_op:
        batch_op.drop_constraint(
            "fk_benchmark_lifecycles_benchmark_id_benchmarks", type_="foreignkey"
        )
    with op.batch_alter_table("benchmark_lifecycles") as batch_op:
        batch_op.create_foreign_key(
            "fk_benchmark_lifecycles_benchmark_id_benchmarks",
            "benchmarks",
            ["benchmark_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("model_outputs") as batch_op:
        batch_op.drop_constraint("fk_model_outputs_atlas_run_id_atlas_runs", type_="foreignkey")
    with op.batch_alter_table("model_outputs") as batch_op:
        batch_op.create_foreign_key(
            "fk_model_outputs_atlas_run_id_atlas_runs",
            "atlas_runs",
            ["atlas_run_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("fk_artifacts_atlas_run_id_atlas_runs", type_="foreignkey")
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "fk_artifacts_atlas_run_id_atlas_runs",
            "atlas_runs",
            ["atlas_run_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.drop_constraint(
            "fk_evaluation_results_model_output_id_model_outputs", type_="foreignkey"
        )
    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.create_foreign_key(
            "fk_evaluation_results_model_output_id_model_outputs",
            "model_outputs",
            ["model_output_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("capability_profiles") as batch_op:
        batch_op.drop_constraint(
            "fk_capability_profiles_atlas_run_id_atlas_runs", type_="foreignkey"
        )
    with op.batch_alter_table("capability_profiles") as batch_op:
        batch_op.create_foreign_key(
            "fk_capability_profiles_atlas_run_id_atlas_runs",
            "atlas_runs",
            ["atlas_run_id"],
            ["id"],
            ondelete="CASCADE",
        )

    with op.batch_alter_table("capability_scores") as batch_op:
        batch_op.drop_constraint(
            "fk_capability_scores_capability_profile_id_capability_profiles", type_="foreignkey"
        )
    with op.batch_alter_table("capability_scores") as batch_op:
        batch_op.create_foreign_key(
            "fk_capability_scores_capability_profile_id_capability_profiles",
            "capability_profiles",
            ["capability_profile_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # 4. JSONB Refactoring (Create detail table, drop old columns)
    op.create_table(
        "evaluation_result_details",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_result_id", sa.Uuid(), nullable=False),
        sa.Column("judge_outputs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("evaluation_logs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["evaluation_result_id"],
            ["evaluation_results.id"],
            name="fk_evaluation_result_details_evaluation_result_id_evaluation_results",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_evaluation_result_details"),
        sa.UniqueConstraint(
            "evaluation_result_id", name="uq_evaluation_result_details_evaluation_result_id"
        ),
    )

    op.drop_column("evaluation_results", "judge_outputs")
    op.drop_column("evaluation_results", "evaluation_logs")


def downgrade() -> None:
    # 4. Reverse JSONB Refactoring
    op.add_column(
        "evaluation_results",
        sa.Column(
            "evaluation_logs",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "evaluation_results",
        sa.Column(
            "judge_outputs",
            postgresql.JSONB(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.drop_table("evaluation_result_details")

    # 3. Reverse Cascade Delete
    with op.batch_alter_table("capability_scores") as batch_op:
        batch_op.drop_constraint(
            "fk_capability_scores_capability_profile_id_capability_profiles", type_="foreignkey"
        )
    with op.batch_alter_table("capability_scores") as batch_op:
        batch_op.create_foreign_key(
            "fk_capability_scores_capability_profile_id_capability_profiles",
            "capability_profiles",
            ["capability_profile_id"],
            ["id"],
        )

    with op.batch_alter_table("capability_profiles") as batch_op:
        batch_op.drop_constraint(
            "fk_capability_profiles_atlas_run_id_atlas_runs", type_="foreignkey"
        )
    with op.batch_alter_table("capability_profiles") as batch_op:
        batch_op.create_foreign_key(
            "fk_capability_profiles_atlas_run_id_atlas_runs", "atlas_runs", ["atlas_run_id"], ["id"]
        )

    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.drop_constraint(
            "fk_evaluation_results_model_output_id_model_outputs", type_="foreignkey"
        )
    with op.batch_alter_table("evaluation_results") as batch_op:
        batch_op.create_foreign_key(
            "fk_evaluation_results_model_output_id_model_outputs",
            "model_outputs",
            ["model_output_id"],
            ["id"],
        )

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_constraint("fk_artifacts_atlas_run_id_atlas_runs", type_="foreignkey")
    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.create_foreign_key(
            "fk_artifacts_atlas_run_id_atlas_runs", "atlas_runs", ["atlas_run_id"], ["id"]
        )

    with op.batch_alter_table("model_outputs") as batch_op:
        batch_op.drop_constraint("fk_model_outputs_atlas_run_id_atlas_runs", type_="foreignkey")
    with op.batch_alter_table("model_outputs") as batch_op:
        batch_op.create_foreign_key(
            "fk_model_outputs_atlas_run_id_atlas_runs", "atlas_runs", ["atlas_run_id"], ["id"]
        )

    with op.batch_alter_table("benchmark_lifecycles") as batch_op:
        batch_op.drop_constraint(
            "fk_benchmark_lifecycles_benchmark_id_benchmarks", type_="foreignkey"
        )
    with op.batch_alter_table("benchmark_lifecycles") as batch_op:
        batch_op.create_foreign_key(
            "fk_benchmark_lifecycles_benchmark_id_benchmarks",
            "benchmarks",
            ["benchmark_id"],
            ["id"],
        )

    # 2. Reverse Unique Constraints
    with op.batch_alter_table("evaluation_strategy_versions") as batch_op:
        batch_op.drop_constraint("uq_strategy_version", type_="unique")
    with op.batch_alter_table("execution_adapter_versions") as batch_op:
        batch_op.drop_constraint("uq_adapter_version", type_="unique")
    with op.batch_alter_table("dataset_versions") as batch_op:
        batch_op.drop_constraint("uq_dataset_version", type_="unique")
    with op.batch_alter_table("benchmark_versions") as batch_op:
        batch_op.drop_constraint("uq_benchmark_version", type_="unique")
    with op.batch_alter_table("configuration_versions") as batch_op:
        batch_op.drop_constraint("uq_configuration_version", type_="unique")

    # 1. Reverse Indexes
    op.drop_index("ix_datasets_name", table_name="datasets")
    op.drop_index("ix_benchmarks_name", table_name="benchmarks")
    op.drop_index("ix_benchmarks_status", table_name="benchmarks")
    op.drop_index("ix_atlas_runs_target_model", table_name="atlas_runs")
    op.drop_index("ix_atlas_runs_status_created_at", table_name="atlas_runs")
