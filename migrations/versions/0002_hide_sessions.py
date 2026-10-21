"""Clear history: study_sessions.hidden_at hides a session from the list, keeping its answers.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("study_sessions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("study_sessions", schema=None) as batch_op:
        batch_op.drop_column("hidden_at")
