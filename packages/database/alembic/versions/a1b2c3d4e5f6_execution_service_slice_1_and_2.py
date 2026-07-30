"""execution_service_slice_1_and_2

Revision ID: a1b2c3d4e5f6
Revises: 27624aa4c089
Create Date: 2026-07-11 13:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "27624aa4c089"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update run_status Enum
    bind = op.get_bind()
    if bind.engine.name == "postgresql":
        op.execute("ALTER TYPE run_status ADD VALUE 'VALIDATING'")
        op.execute("ALTER TYPE run_status ADD VALUE 'ABORTING'")

    # 2. Create new Enums
    task_status_enum = postgresql.ENUM(
        "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED", name="task_status"
    )

    worker_status_enum = postgresql.ENUM(
        "REGISTERED", "READY", "BUSY", "OFFLINE", name="worker_status"
    )

    event_type_enum = postgresql.ENUM(
        "RUN_CREATED",
        "RUN_VALIDATED",
        "RUN_QUEUED",
        "RUN_STARTED",
        "RUN_PAUSED",
        "RUN_RESUMED",
        "RUN_FAILED",
        "RUN_COMPLETED",
        "RUN_CANCELLED",
        "TASK_QUEUED",
        "TASK_ASSIGNED",
        "TASK_STARTED",
        "TASK_COMPLETED",
        "TASK_FAILED",
        "WORKER_HEARTBEAT",
        "WORKER_REGISTERED",
        "WORKER_OFFLINE",
        name="event_type",
    )

    # 3. Create execution_workers table
    op.create_table(
        "execution_workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("adapter_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", worker_status_enum, nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hardware_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=True),
        sa.Column("current_load", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("health", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["adapter_id"], ["execution_adapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_execution_workers_adapter_id"), "execution_workers", ["adapter_id"], unique=False
    )

    # 4. Create atlas_tasks table
    op.create_table(
        "atlas_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("atlas_run_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_worker_id", sa.Uuid(), nullable=True),
        sa.Column("status", task_status_enum, nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["atlas_run_id"], ["atlas_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["assigned_worker_id"], ["execution_workers.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_atlas_tasks_atlas_run_id"), "atlas_tasks", ["atlas_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_atlas_tasks_assigned_worker_id"),
        "atlas_tasks",
        ["assigned_worker_id"],
        unique=False,
    )

    # 5. Create run_events table
    op.create_table(
        "run_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("atlas_run_id", sa.Uuid(), nullable=False),
        sa.Column("atlas_task_id", sa.Uuid(), nullable=True),
        sa.Column("execution_worker_id", sa.Uuid(), nullable=True),
        sa.Column("type", event_type_enum, nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["atlas_run_id"], ["atlas_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["atlas_task_id"], ["atlas_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["execution_worker_id"], ["execution_workers.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_run_events_atlas_run_id"), "run_events", ["atlas_run_id"], unique=False
    )
    op.create_index(
        op.f("ix_run_events_atlas_task_id"), "run_events", ["atlas_task_id"], unique=False
    )
    op.create_index(
        op.f("ix_run_events_execution_worker_id"),
        "run_events",
        ["execution_worker_id"],
        unique=False,
    )
    op.create_index(op.f("ix_run_events_type"), "run_events", ["type"], unique=False)

    # 6. Alter atlas_runs table
    op.add_column(
        "atlas_runs", sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "atlas_runs", sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("atlas_runs", sa.Column("error_message", sa.String(), nullable=True))

    # 7. Update model_outputs table to reference atlas_tasks
    if bind.engine.name == "sqlite":
        with op.batch_alter_table("model_outputs") as batch_op:
            batch_op.add_column(sa.Column("atlas_task_id", sa.Uuid(), nullable=True))
            batch_op.create_foreign_key(
                "fk_model_outputs_atlas_task_id",
                "atlas_tasks",
                ["atlas_task_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_index(
                op.f("ix_model_outputs_atlas_task_id"), ["atlas_task_id"], unique=False
            )
    else:
        op.add_column("model_outputs", sa.Column("atlas_task_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_model_outputs_atlas_task_id",
            "model_outputs",
            "atlas_tasks",
            ["atlas_task_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index(
            op.f("ix_model_outputs_atlas_task_id"), "model_outputs", ["atlas_task_id"], unique=False
        )


def downgrade() -> None:
    # 7. Revert model_outputs
    op.drop_index(op.f("ix_model_outputs_atlas_task_id"), table_name="model_outputs")
    op.drop_constraint("fk_model_outputs_atlas_task_id", "model_outputs", type_="foreignkey")
    op.drop_column("model_outputs", "atlas_task_id")

    # 6. Revert atlas_runs
    op.drop_column("atlas_runs", "error_message")
    op.drop_column("atlas_runs", "config")
    op.drop_column("atlas_runs", "last_heartbeat_at")

    # 5. Drop run_events
    op.drop_index(op.f("ix_run_events_type"), table_name="run_events")
    op.drop_index(op.f("ix_run_events_execution_worker_id"), table_name="run_events")
    op.drop_index(op.f("ix_run_events_atlas_task_id"), table_name="run_events")
    op.drop_index(op.f("ix_run_events_atlas_run_id"), table_name="run_events")
    op.drop_table("run_events")

    # 4. Drop atlas_tasks
    op.drop_index(op.f("ix_atlas_tasks_assigned_worker_id"), table_name="atlas_tasks")
    op.drop_index(op.f("ix_atlas_tasks_atlas_run_id"), table_name="atlas_tasks")
    op.drop_table("atlas_tasks")

    # 3. Drop execution_workers
    op.drop_index(op.f("ix_execution_workers_adapter_id"), table_name="execution_workers")
    op.drop_table("execution_workers")

    # 2. Drop Enums
    postgresql.ENUM(name="event_type").drop(op.get_bind())
    postgresql.ENUM(name="worker_status").drop(op.get_bind())
    postgresql.ENUM(name="task_status").drop(op.get_bind())

    # 1. We cannot easily drop values from an ENUM type in Postgres. We ignore downgrade for run_status.
