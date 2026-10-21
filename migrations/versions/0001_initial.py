"""Initial schema: users, login sessions and practice state (spec 06, ruling R2).

Revision ID: 0001
Revises:
Create Date: 2026-10-21 10:15:13.784842
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "study_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("topics", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("study_sessions", schema=None) as batch_op:
        batch_op.create_index("ix_study_sessions_user_id", ["user_id"], unique=False)

    op.create_table(
        "web_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_table(
        "session_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.String(length=128), nullable=False),
        sa.Column("content_version", sa.String(length=12), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tries_used", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["study_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence", name="uq_session_items_session_sequence"),
    )
    with op.batch_alter_table("session_items", schema=None) as batch_op:
        batch_op.create_index(
            "ix_session_items_session_id_state", ["session_id", "state"], unique=False
        )

    op.create_table(
        "item_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_item_id"],
            ["session_items.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("answer_kind", sa.String(length=32), nullable=False),
        sa.Column("answer_json", sa.Text(), nullable=False),
        sa.Column("answer_latex", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_item_id"],
            ["session_items.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id"),
    )
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.create_index("ix_submissions_session_item_id", ["session_item_id"], unique=False)

    op.create_table(
        "attempt_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_pk", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("verifier_version", sa.String(length=64), nullable=False),
        sa.Column("worker_ms", sa.Integer(), nullable=False),
        sa.Column("queue_ms", sa.Integer(), nullable=False),
        sa.Column("seconds_on_item", sa.Integer(), nullable=False),
        sa.Column("counts_as_try", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["submission_pk"],
            ["submissions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_pk"),
    )


def downgrade() -> None:
    op.drop_table("attempt_results")
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index("ix_submissions_session_item_id")

    op.drop_table("submissions")
    op.drop_table("item_events")
    with op.batch_alter_table("session_items", schema=None) as batch_op:
        batch_op.drop_index("ix_session_items_session_id_state")

    op.drop_table("session_items")
    op.drop_table("web_sessions")
    with op.batch_alter_table("study_sessions", schema=None) as batch_op:
        batch_op.drop_index("ix_study_sessions_user_id")

    op.drop_table("study_sessions")
    op.drop_table("users")
