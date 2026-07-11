"""implement_readiness_review

Revision ID: 27624aa4c089
Revises: 4007056c9559
Create Date: 2026-07-11 17:56:39.664254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27624aa4c089'
down_revision: Union[str, Sequence[str], None] = '4007056c9559'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. New Indexes
    op.create_index('ix_atlas_runs_status_created_at', 'atlas_runs', ['status', 'created_at'])
    op.create_index('ix_atlas_runs_target_model', 'atlas_runs', ['target_model'])
    op.create_index('ix_benchmarks_status', 'benchmarks', ['status'])
    op.create_index('ix_benchmarks_name', 'benchmarks', ['name'])
    op.create_index('ix_datasets_name', 'datasets', ['name'])

    # 2. Unique Constraints
    op.create_unique_constraint('uq_configuration_version', 'configuration_versions', ['configuration_id', 'version_string'])
    op.create_unique_constraint('uq_benchmark_version', 'benchmark_versions', ['benchmark_id', 'version_string'])
    op.create_unique_constraint('uq_dataset_version', 'dataset_versions', ['dataset_id', 'version_string'])
    op.create_unique_constraint('uq_adapter_version', 'execution_adapter_versions', ['adapter_id', 'version_string'])
    op.create_unique_constraint('uq_strategy_version', 'evaluation_strategy_versions', ['strategy_id', 'version_string'])

    # 3. Cascade Delete (Drop Restrict, Add Cascade)
    op.drop_constraint('fk_benchmark_lifecycles_benchmark_id_benchmarks', 'benchmark_lifecycles', type_='foreignkey')
    op.create_foreign_key('fk_benchmark_lifecycles_benchmark_id_benchmarks', 'benchmark_lifecycles', 'benchmarks', ['benchmark_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('fk_model_outputs_atlas_run_id_atlas_runs', 'model_outputs', type_='foreignkey')
    op.create_foreign_key('fk_model_outputs_atlas_run_id_atlas_runs', 'model_outputs', 'atlas_runs', ['atlas_run_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('fk_artifacts_atlas_run_id_atlas_runs', 'artifacts', type_='foreignkey')
    op.create_foreign_key('fk_artifacts_atlas_run_id_atlas_runs', 'artifacts', 'atlas_runs', ['atlas_run_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('fk_evaluation_results_model_output_id_model_outputs', 'evaluation_results', type_='foreignkey')
    op.create_foreign_key('fk_evaluation_results_model_output_id_model_outputs', 'evaluation_results', 'model_outputs', ['model_output_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('fk_capability_profiles_atlas_run_id_atlas_runs', 'capability_profiles', type_='foreignkey')
    op.create_foreign_key('fk_capability_profiles_atlas_run_id_atlas_runs', 'capability_profiles', 'atlas_runs', ['atlas_run_id'], ['id'], ondelete='CASCADE')

    op.drop_constraint('fk_capability_scores_capability_profile_id_capability_profiles', 'capability_scores', type_='foreignkey')
    op.create_foreign_key('fk_capability_scores_capability_profile_id_capability_profiles', 'capability_scores', 'capability_profiles', ['capability_profile_id'], ['id'], ondelete='CASCADE')

    # 4. JSONB Refactoring (Create detail table, drop old columns)
    op.create_table(
        'evaluation_result_details',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('evaluation_result_id', sa.Uuid(), nullable=False),
        sa.Column('judge_outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation_logs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['evaluation_result_id'], ['evaluation_results.id'], name='fk_evaluation_result_details_evaluation_result_id_evaluation_results', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_evaluation_result_details'),
        sa.UniqueConstraint('evaluation_result_id', name='uq_evaluation_result_details_evaluation_result_id')
    )

    op.drop_column('evaluation_results', 'judge_outputs')
    op.drop_column('evaluation_results', 'evaluation_logs')


def downgrade() -> None:
    # 4. Reverse JSONB Refactoring
    op.add_column('evaluation_results', sa.Column('evaluation_logs', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('evaluation_results', sa.Column('judge_outputs', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.drop_table('evaluation_result_details')

    # 3. Reverse Cascade Delete
    op.drop_constraint('fk_capability_scores_capability_profile_id_capability_profiles', 'capability_scores', type_='foreignkey')
    op.create_foreign_key('fk_capability_scores_capability_profile_id_capability_profiles', 'capability_scores', 'capability_profiles', ['capability_profile_id'], ['id'])

    op.drop_constraint('fk_capability_profiles_atlas_run_id_atlas_runs', 'capability_profiles', type_='foreignkey')
    op.create_foreign_key('fk_capability_profiles_atlas_run_id_atlas_runs', 'capability_profiles', 'atlas_runs', ['atlas_run_id'], ['id'])

    op.drop_constraint('fk_evaluation_results_model_output_id_model_outputs', 'evaluation_results', type_='foreignkey')
    op.create_foreign_key('fk_evaluation_results_model_output_id_model_outputs', 'evaluation_results', 'model_outputs', ['model_output_id'], ['id'])

    op.drop_constraint('fk_artifacts_atlas_run_id_atlas_runs', 'artifacts', type_='foreignkey')
    op.create_foreign_key('fk_artifacts_atlas_run_id_atlas_runs', 'artifacts', 'atlas_runs', ['atlas_run_id'], ['id'])

    op.drop_constraint('fk_model_outputs_atlas_run_id_atlas_runs', 'model_outputs', type_='foreignkey')
    op.create_foreign_key('fk_model_outputs_atlas_run_id_atlas_runs', 'model_outputs', 'atlas_runs', ['atlas_run_id'], ['id'])

    op.drop_constraint('fk_benchmark_lifecycles_benchmark_id_benchmarks', 'benchmark_lifecycles', type_='foreignkey')
    op.create_foreign_key('fk_benchmark_lifecycles_benchmark_id_benchmarks', 'benchmark_lifecycles', 'benchmarks', ['benchmark_id'], ['id'])

    # 2. Reverse Unique Constraints
    op.drop_constraint('uq_strategy_version', 'evaluation_strategy_versions', type_='unique')
    op.drop_constraint('uq_adapter_version', 'execution_adapter_versions', type_='unique')
    op.drop_constraint('uq_dataset_version', 'dataset_versions', type_='unique')
    op.drop_constraint('uq_benchmark_version', 'benchmark_versions', type_='unique')
    op.drop_constraint('uq_configuration_version', 'configuration_versions', type_='unique')

    # 1. Reverse Indexes
    op.drop_index('ix_datasets_name', table_name='datasets')
    op.drop_index('ix_benchmarks_name', table_name='benchmarks')
    op.drop_index('ix_benchmarks_status', table_name='benchmarks')
    op.drop_index('ix_atlas_runs_target_model', table_name='atlas_runs')
    op.drop_index('ix_atlas_runs_status_created_at', table_name='atlas_runs')
