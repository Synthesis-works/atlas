"""add unique index for credit transaction reference idempotency

Revision ID: 7d4a9c2f6e81
Revises: 3f9c71a2e8b4
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d4a9c2f6e81"
down_revision: str | Sequence[str] | None = "3f9c71a2e8b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Exactly-once entitlement grants: at most one CreditTransaction may
    # reference a given domain entity (e.g. a Payment id). The partial index
    # leaves rows without a reference untouched.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_credit_transactions_reference
        ON credit_transactions (reference_type, reference_id)
        WHERE reference_type IS NOT NULL AND reference_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_credit_transactions_reference")
