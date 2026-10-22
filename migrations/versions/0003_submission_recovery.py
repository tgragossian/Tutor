"""Submission recovery: reserved revision and a recovery lease (review B-R2 / B-R5).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added columns only (SQLite ADD COLUMN): no table rebuild, so foreign keys stay intact.
    # Existing rows get reserved_revision NULL; recovery treats those as stale, never guessed.
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("reserved_revision", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("lease", sa.Integer(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("leased_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_column("leased_at")
        batch_op.drop_column("lease")
        batch_op.drop_column("reserved_revision")
