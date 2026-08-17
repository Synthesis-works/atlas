"""d7_snapshot_idempotency

Revision ID: cb618b624b42
Revises: 02f16730fe4f
Create Date: 2026-08-15 19:48:23.805131

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cb618b624b42"
down_revision: str | Sequence[str] | None = "02f16730fe4f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Resolve existing automatic duplicates gracefully preserving newest
    op.execute("""
        DELETE FROM leaderboard_snapshots
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                ROW_NUMBER() OVER (
                    PARTITION BY target_id, (metadata->>'execution_id_trigger')
                    ORDER BY snapshot_timestamp DESC
                ) as rn
                FROM leaderboard_snapshots
                WHERE metadata->>'execution_id_trigger' IS NOT NULL
            ) t
            WHERE t.rn > 1
        )
    """)

    # 2. Drop if a previous (non-partial) version of the index exists
    op.execute("DROP INDEX IF EXISTS uq_snapshot_target_exec")

    # 3. Inject precise PARTIAL unique index (only for automated snapshots with a non-NULL trigger)
    #    NULL execution_id_trigger rows (manual snapshots) are excluded from this constraint.
    op.execute("""
        CREATE UNIQUE INDEX uq_snapshot_target_exec
        ON leaderboard_snapshots (target_id, (metadata->>'execution_id_trigger'))
        WHERE metadata->>'execution_id_trigger' IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_snapshot_target_exec")
