"""add paypal to payment_provider enum

Revision ID: 3f9c71a2e8b4
Revises: 81db55ad9a77
Create Date: 2026-08-20 00:00:00.000000

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3f9c71a2e8b4"
down_revision: str | Sequence[str] | None = "81db55ad9a77"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The `payment_provider` native Postgres ENUM stores the enum member *names*
# (STRIPE / RAZORPAY / MANUAL), as created by the immutable baseline migration
# 7537275102f0. The new value must therefore be added as the upper-case member
# name that the SQLAlchemy Enum maps from PaymentProvider.PAYPAL.
# See docs/database/ENUM_POLICY.md.
ENUM_NAME = "payment_provider"
NEW_VALUE = "PAYPAL"


def upgrade() -> None:
    # ALTER TYPE cannot run inside a transaction block; use the autocommit
    # block as mandated by the repository ENUM policy. `IF NOT EXISTS` keeps
    # this idempotent against the SQLite/dev `create_all` path where the type
    # is created directly from the (already updated) model metadata.
    with op.get_context().autocommit_block():
        op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")


def downgrade() -> None:
    # PostgreSQL does not support dropping an enum value cheaply (requires a
    # multi-step rename/rebuild). Per docs/database/ENUM_POLICY.md, enum
    # additions are treated as IRREVERSIBLE.
    pass