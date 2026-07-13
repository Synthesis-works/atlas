"""Add evaluation schema

Revision ID: 375aa9bc04ec
Revises: a1b2c3d4e5f6
Create Date: 2026-07-13 13:02:14.244227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '375aa9bc04ec'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('capability_definitions', sa.Column('id', sa.UUID(),
        nullable=False), sa.Column('name', sa.String(), nullable=False), sa.
        Column('description', sa.String(), nullable=True), sa.
        PrimaryKeyConstraint('id', name=op.f('pk_capability_definitions')), sa.
        UniqueConstraint('name', name=op.f('uq_capability_definitions_name')))
    op.create_table('capability_profiles', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('adapter_version_id', sa.UUID(), nullable=False), sa.
        Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.
        PrimaryKeyConstraint('id', name=op.f('pk_capability_profiles')))
    op.create_index(op.f('ix_capability_profiles_adapter_version_id'),
        'capability_profiles', ['adapter_version_id'], unique=False)
    op.create_table('evaluation_jobs', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('atlas_run_id', sa.UUID(), nullable=False), sa.Column
    ('status', sa.Enum('PENDING', 'EVALUATING', 'COMPLETED', 'FAILED',
        'ABORTED', name='evaluationjobstatus'), nullable=False), sa.Column(
        'created_at', sa.DateTime(timezone=True), nullable=False), sa.Column(
        'updated_at', sa.DateTime(timezone=True), nullable=False), sa.
        PrimaryKeyConstraint('id', name=op.f('pk_evaluation_jobs')))
    op.create_index(op.f('ix_evaluation_jobs_atlas_run_id'), 'evaluation_jobs',
    ['atlas_run_id'], unique=False)
    op.create_index(op.f('ix_evaluation_jobs_status'), 'evaluation_jobs', [
        'status'], unique=False)
    op.create_table('evaluation_pipelines', sa.Column('id', sa.UUID(), nullable
    =False), sa.Column('name', sa.String(), nullable=False), sa.Column(
        'description', sa.String(), nullable=True), sa.PrimaryKeyConstraint(
        'id', name=op.f('pk_evaluation_pipelines')), sa.UniqueConstraint('name',
    name=op.f('uq_evaluation_pipelines_name')))
    op.create_table('judges', sa.Column('id', sa.UUID(), nullable=False), sa.
        Column('name', sa.String(), nullable=False), sa.Column('provider', sa.
    String(), nullable=True), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_judges')), sa.UniqueConstraint('name', name=op.f('uq_judges_name')))
    op.create_table('metric_definitions', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('name', sa.String(), nullable=False), sa.Column(
        'version', sa.String(), nullable=False), sa.Column('category', sa.Enum(
        'CORRECTNESS', 'PERFORMANCE', 'EFFICIENCY', 'SAFETY', 'QUALITY', 'COST',
    name='metriccategory'), nullable=False), sa.Column('direction', sa.Enum
    ('HIGHER_IS_BETTER', 'LOWER_IS_BETTER', 'NEUTRAL', name=
        'metricdirection'), nullable=False), sa.Column('unit', sa.String(),
        nullable=False), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_metric_definitions')), sa.UniqueConstraint('name', 'version', name=
        'uq_metric_definition_version'))
    op.create_table('capability_scores', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('profile_id', sa.UUID(), nullable=False), sa.Column(
        'capability_definition_id', sa.UUID(), nullable=False), sa.Column(
        'score', sa.Float(), nullable=False), sa.Column('confidence', sa.Float(
        ), nullable=True), sa.ForeignKeyConstraint(['capability_definition_id'],
    ['capability_definitions.id'], name=op.f(
        'fk_capability_scores_capability_definition_id_capability_definitions'),
    ondelete='RESTRICT'), sa.ForeignKeyConstraint(['profile_id'], [
        'capability_profiles.id'], name=op.f(
        'fk_capability_scores_profile_id_capability_profiles'), ondelete=
        'CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_capability_scores')), sa.UniqueConstraint('profile_id',
        'capability_definition_id', name='uq_capability_score'))
    op.create_table('evaluation_pipeline_versions', sa.Column('id', sa.UUID(),
        nullable=False), sa.Column('pipeline_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.String(), nullable=False), sa.Column(
        'config_schema', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.ForeignKeyConstraint(['pipeline_id'], ['evaluation_pipelines.id'],
    name=op.f(
        'fk_evaluation_pipeline_versions_pipeline_id_evaluation_pipelines'),
    ondelete='CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_evaluation_pipeline_versions')), sa.UniqueConstraint('pipeline_id',
        'version', name='uq_eval_pipeline_version'))
    op.create_table('judge_versions', sa.Column('id', sa.UUID(), nullable=False
        ), sa.Column('judge_id', sa.UUID(), nullable=False), sa.Column(
        'version', sa.String(), nullable=False), sa.ForeignKeyConstraint([
        'judge_id'], ['judges.id'], name=op.f(
        'fk_judge_versions_judge_id_judges'), ondelete='CASCADE'), sa.
        PrimaryKeyConstraint('id', name=op.f('pk_judge_versions')), sa.
        UniqueConstraint('judge_id', 'version', name='uq_judge_version'))
    op.create_table('evaluation_attempts', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('job_id', sa.UUID(), nullable=False), sa.Column(
        'pipeline_version_id', sa.UUID(), nullable=False), sa.Column(
        'attempt_number', sa.Integer(), nullable=False), sa.Column('status', sa
    .Enum('QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', name='attemptstatus'),
        nullable=False), sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True), sa.
        Column('completed_at', sa.DateTime(timezone=True), nullable=True), sa.
        ForeignKeyConstraint(['job_id'], ['evaluation_jobs.id'], name=op.f(
        'fk_evaluation_attempts_job_id_evaluation_jobs'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pipeline_version_id'], [
        'evaluation_pipeline_versions.id'], name=op.f(
        'fk_evaluation_attempts_pipeline_version_id_evaluation_pipeline_versions'
        ), ondelete='RESTRICT'), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_evaluation_attempts')), sa.UniqueConstraint('job_id',
        'attempt_number', name='uq_eval_attempt_number'))
    op.create_index(op.f('ix_evaluation_attempts_job_id'),
        'evaluation_attempts', ['job_id'], unique=False)
    op.create_index(op.f('ix_evaluation_attempts_pipeline_version_id'),
        'evaluation_attempts', ['pipeline_version_id'], unique=False)
    op.create_index(op.f('ix_evaluation_attempts_status'),
        'evaluation_attempts', ['status'], unique=False)
    op.create_table('evaluation_artifacts', sa.Column('id', sa.UUID(), nullable
    =False), sa.Column('attempt_id', sa.UUID(), nullable=False), sa.Column(
        'artifact_hash', sa.String(), nullable=False), sa.Column(
        'target_output', postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column('reference_data', postgresql.JSONB(astext_type=Text()),
        nullable=True), sa.Column('context', postgresql.JSONB(astext_type=Text(
        )), nullable=True), sa.ForeignKeyConstraint(['attempt_id'], [
        'evaluation_attempts.id'], name=op.f(
        'fk_evaluation_artifacts_attempt_id_evaluation_attempts'), ondelete=
        'CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_evaluation_artifacts')))
    op.create_table('evaluation_results', sa.Column('id', sa.UUID(), nullable=
    False), sa.Column('attempt_id', sa.UUID(), nullable=False), sa.Column(
        'artifacts_data', postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column('warnings', postgresql.JSONB(astext_type=Text()), nullable=
    True), sa.Column('metadata_', postgresql.JSONB(astext_type=Text()),
        nullable=True), sa.ForeignKeyConstraint(['attempt_id'], [
        'evaluation_attempts.id'], name=op.f(
        'fk_evaluation_results_attempt_id_evaluation_attempts'), ondelete=
        'CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f(
        'pk_evaluation_results')), sa.UniqueConstraint('attempt_id', name=op.f(
        'uq_evaluation_results_attempt_id')))
    op.create_table('judge_traces', sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('result_id', sa.UUID(), nullable=False), sa.Column(
        'judge_version_id', sa.UUID(), nullable=False), sa.Column('prompt', sa.
    String(), nullable=False), sa.Column('response', sa.String(), nullable=
    False), sa.Column('rubric', sa.String(), nullable=False), sa.Column(
        'reasoning', sa.String(), nullable=False), sa.Column('latency_ms', sa.
    Float(), nullable=True), sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('metadata_', postgresql.JSONB(astext_type=Text()), nullable=
    True), sa.ForeignKeyConstraint(['judge_version_id'], [
        'judge_versions.id'], name=op.f(
        'fk_judge_traces_judge_version_id_judge_versions'), ondelete='RESTRICT'
        ), sa.ForeignKeyConstraint(['result_id'], ['evaluation_results.id'],
    name=op.f('fk_judge_traces_result_id_evaluation_results'), ondelete=
        'CASCADE'), sa.PrimaryKeyConstraint('id', name=op.f('pk_judge_traces')))
    op.create_table('metric_values', sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('result_id', sa.UUID(), nullable=False), sa.Column(
        'metric_def_id', sa.UUID(), nullable=False), sa.Column('raw_value', sa.
    Float(), nullable=False), sa.Column('normalized_value', sa.Float(),
        nullable=False), sa.Column('source', sa.String(), nullable=False), sa.
        Column('aggregation', sa.String(), nullable=False), sa.Column(
        'confidence', sa.Float(), nullable=True), sa.Column('metadata_',
        postgresql.JSONB(astext_type=Text()), nullable=True), sa.
        ForeignKeyConstraint(['metric_def_id'], ['metric_definitions.id'], name
    =op.f('fk_metric_values_metric_def_id_metric_definitions'), ondelete=
        'RESTRICT'), sa.ForeignKeyConstraint(['result_id'], [
        'evaluation_results.id'], name=op.f(
        'fk_metric_values_result_id_evaluation_results'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_metric_values')))
    op.create_index(op.f('ix_metric_values_metric_def_id'), 'metric_values', [
        'metric_def_id'], unique=False)
    op.create_index(op.f('ix_metric_values_source'), 'metric_values', ['source'
    ], unique=False)



def downgrade() -> None:
    op.drop_table('judges')
    op.drop_table('evaluation_pipelines')
    op.drop_table('metric_values')
    op.drop_table('judge_traces')
    op.drop_table('capability_definitions')
    op.drop_table('evaluation_artifacts')
    op.drop_table('evaluation_results')
    op.drop_table('metric_definitions')
    op.drop_table('capability_scores')
    op.drop_table('evaluation_jobs')
    op.drop_table('judge_versions')
    op.drop_table('evaluation_pipeline_versions')
    op.drop_table('capability_profiles')
    op.drop_table('evaluation_attempts')
