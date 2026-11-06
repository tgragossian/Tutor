"""Hint ladder by mistakes made (spec D6, D9, D10).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05

The ladder now reads ``answers.mistake_type``: a type's level is the number of applied wrong
answers of that type on the presentation, capped at 3, and one hint is given per attempt.
``help_requests.answer_id`` is the latest applied wrong answer at admission (NULL when none;
old rows stay NULL). ``item_help_state`` drops the R35 hint counters (``hint_attempt_pk``,
``hint_type``, ``hint_counts``, ``hint_level``) and keeps ``start_hints``, ``help_seq`` and
``in_flight``. The downgrade re-adds the counters with their old types and defaults; their
values are not rebuilt.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.add_column(sa.Column("answer_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_help_requests_answer_id_answers", "answers", ["answer_id"], ["id"]
        )
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.drop_column("hint_counts")
        batch_op.drop_column("hint_type")
        batch_op.drop_column("hint_attempt_pk")
        batch_op.drop_column("hint_level")


def downgrade() -> None:
    with op.batch_alter_table("item_help_state", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("hint_level", sa.Integer(), server_default="1", nullable=False)
        )
        batch_op.add_column(sa.Column("hint_attempt_pk", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hint_type", sa.String(length=16), nullable=True))
        batch_op.add_column(
            sa.Column("hint_counts", sa.JSON(), server_default="{}", nullable=False)
        )
    with op.batch_alter_table("help_requests", schema=None) as batch_op:
        batch_op.drop_constraint("fk_help_requests_answer_id_answers", type_="foreignkey")
        batch_op.drop_column("answer_id")
