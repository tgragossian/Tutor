"""Hint ladder by mistake: which wrong attempt the last hint addressed, and the model's call.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-27

``item_help_state.hint_attempt_pk`` is the latest wrong submission the last delivered hint was
about (null until a hint follows a wrong answer). ``help_requests.hint_mistake`` records the
model's "same" or "new" when it was asked to judge a new wrong attempt (ruling R35).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added columns only (SQLite ADD COLUMN), nullable: existing rows need no value.
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hint_attempt_pk", sa.Integer(), nullable=True))
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hint_mistake", sa.String(length=8), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.drop_column("hint_mistake")
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.drop_column("hint_attempt_pk")
