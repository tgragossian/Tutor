"""Hint ladder by mistake type (ruling R35).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27

``item_help_state``: ``hint_attempt_pk`` is the latest wrong submission the last delivered
hint addressed, ``hint_type`` that attempt's mistake type, and ``hint_counts`` the number of
delivered hints per mistake type on this presentation (``{"algebra": 1, ...}``), and
``start_hints`` the level-0 hints delivered before any wrong answer (step 1, then 2).
``help_requests.mistake_type`` records the type a classifying hint used and
``start_step`` the level-0 step (1 or 2). Added columns only;
not yet deployed anywhere, so revised in place on 2026-10-27 (same/new became types).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hint_attempt_pk", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hint_type", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column("hint_counts", sa.JSON(), server_default="{}", nullable=False)
        )
        batch_op.add_column(
            sa.Column("start_hints", sa.Integer(), server_default="0", nullable=False)
        )
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("mistake_type", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("start_step", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.drop_column("start_step")
        batch_op.drop_column("mistake_type")
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.drop_column("start_hints")
        batch_op.drop_column("hint_counts")
        batch_op.drop_column("hint_type")
        batch_op.drop_column("hint_attempt_pk")
