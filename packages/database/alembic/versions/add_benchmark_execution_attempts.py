"""Add benchmark_execution_attempts table with provenance telemetry

Revision ID: add_benchmark_execution_attempts
Revises: 7d4a9c2f6e81
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_benchmark_execution_attempts'
down_revision: str | Sequence[str] | None = '7d4a9c2f6e81'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    attempt_status_enum = postgresql.ENUM(
        'PENDING', 'CONTAINER_CREATED', 'RUNNING', 'COMPLETED',
        'FAILED', 'TIMED_OUT', 'CANCELLED', 'CLEANED',
        name='attempt_status', create_type=True
    )
    attempt_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'benchmark_execution_attempts',
        sa.Column('execution_id', sa.UUID(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('status', attempt_status_enum, nullable=False),
        sa.Column('executor_type', sa.String(length=50), nullable=False),
        sa.Column('container_id', sa.String(length=255), nullable=True),
        sa.Column('image_ref', sa.String(length=500), nullable=True),
        sa.Column('image_digest', sa.String(length=500), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exit_code', sa.Integer(), nullable=True),
        sa.Column('termination_reason', sa.String(length=100), nullable=True),
        sa.Column('oom_killed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('timed_out', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('cpu_seconds', sa.Float(), nullable=True),
        sa.Column('peak_memory_bytes', sa.BigInteger(), nullable=True),
        sa.Column('pids_peak', sa.Integer(), nullable=True),
        sa.Column('network_rx_bytes', sa.BigInteger(), nullable=True),
        sa.Column('network_tx_bytes', sa.BigInteger(), nullable=True),
        sa.Column('trace_id', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=255), nullable=True),
        sa.Column('worker_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('updated_by_id', sa.UUID(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_benchmark_execution_attempts_created_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['execution_id'], ['executions.id'], name=op.f('fk_benchmark_execution_attempts_execution_id_executions'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_id'], ['users.id'], name=op.f('fk_benchmark_execution_attempts_updated_by_id_users'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_benchmark_execution_attempts'))
    )
    op.create_index(
        op.f('ix_benchmark_execution_attempts_execution_id'),
        'benchmark_execution_attempts', ['execution_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f('ix_benchmark_execution_attempts_execution_id'),
        table_name='benchmark_execution_attempts'
    )
    op.drop_table('benchmark_execution_attempts')
    attempt_status_enum = postgresql.ENUM(
        'PENDING', 'CONTAINER_CREATED', 'RUNNING', 'COMPLETED',
        'FAILED', 'TIMED_OUT', 'CANCELLED', 'CLEANED',
        name='attempt_status'
    )
    attempt_status_enum.drop(op.get_bind(), checkfirst=True)
