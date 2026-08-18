"""rls default deny for backend-only tables

Revision ID: 81db55ad9a77
Revises: 7537275102f0
Create Date: 2026-08-18 15:39:33.212181

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "81db55ad9a77"
down_revision: str | Sequence[str] | None = "7537275102f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Exact public-schema table list captured from the live Supabase project
# (information_schema.tables, table_type = 'BASE TABLE', 65 tables including
# alembic_version). Atlas is backend-only: the browser talks exclusively to
# the FastAPI application, which connects as the table-owning postgres role
# and therefore bypasses row-level security. Enabling RLS without any
# policies makes the Supabase PostgREST surface (anon/authenticated roles)
# deny-by-default without affecting the application or the worker.
RLS_TABLES: tuple[str, ...] = (
    "agent_task_records",
    "alembic_version",
    "artifacts",
    "audit_logs",
    "benchmark_capability_link",
    "benchmark_categories",
    "benchmark_category_link",
    "benchmark_lifecycles",
    "benchmark_version_dataset_link",
    "benchmark_versions",
    "benchmarks",
    "capabilities",
    "capability_profiles",
    "capability_scores",
    "configuration_versions",
    "configurations",
    "constraints",
    "credit_accounts",
    "credit_transactions",
    "dataset_export_actions",
    "dataset_licenses",
    "dataset_registries",
    "dataset_sources",
    "dataset_versions",
    "datasets",
    "ee_executions",
    "evaluation_artifacts",
    "evaluation_result_details",
    "evaluation_results",
    "evaluation_rules",
    "evaluation_strategies",
    "evaluation_strategy_versions",
    "execution_adapter_versions",
    "execution_adapters",
    "execution_artifacts",
    "execution_attempts",
    "execution_leases",
    "executions",
    "features",
    "invitations",
    "invoices",
    "judges",
    "leaderboard_snapshot_entries",
    "leaderboard_snapshots",
    "model_outputs",
    "notifications",
    "organization_members",
    "organizations",
    "outbox_messages",
    "payments",
    "price_features",
    "prices",
    "products",
    "projects",
    "prompts",
    "refunds",
    "report_metrics",
    "report_versions",
    "reports",
    "subscriptions",
    "tasks",
    "test_cases",
    "usage_records",
    "users",
    "webhook_events",
)


def upgrade() -> None:
    """Enable row-level security (deny-by-default) on all backend-only tables."""
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security on all tables enabled by this migration."""
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
