"""Help requests, per-item help state, privacy epoch and the usage ledger.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added column only (SQLite ADD COLUMN); existing users start at epoch 0.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("privacy_epoch", sa.Integer(), server_default="0", nullable=False)
        )

    op.create_table(
        "item_help_state",
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("hint_level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("help_seq", sa.Integer(), server_default="0", nullable=False),
        sa.Column("in_flight", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["session_item_id"], ["session_items.id"]),
        sa.PrimaryKeyConstraint("session_item_id"),
    )
    op.create_table(
        "help_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("item_revision", sa.Integer(), nullable=False),
        sa.Column("help_type", sa.String(length=32), nullable=False),
        sa.Column("confusion_id", sa.String(length=64), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("privacy_epoch", sa.Integer(), nullable=False),
        sa.Column("help_seq", sa.Integer(), nullable=False),
        sa.Column("hint_level", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("prompt_version", sa.String(length=32), nullable=False),
        sa.Column("corpus_hash", sa.String(length=64), nullable=False),
        sa.Column("index_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("retrieved_ids", sa.JSON(), nullable=False),
        sa.Column("cited_ids", sa.JSON(), nullable=False),
        sa.Column("guard_counts", sa.JSON(), nullable=False),
        sa.Column("calls", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("arm", sa.String(length=16), server_default="none", nullable=False),
        sa.Column("serving_model", sa.String(length=64), nullable=True),
        sa.Column("output_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_submission_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["session_item_id"], ["session_items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_help_requests_user_id", "help_requests", ["user_id"])
    op.create_index("ix_help_requests_session_item_id", "help_requests", ["session_item_id"])
    op.create_table(
        "usage_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("call_no", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("month", sa.String(length=7), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("reserved_micros", sa.Integer(), nullable=False),
        sa.Column("settled_micros", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "call_no", name="uq_usage_entries_request_call"),
    )
    op.create_index(
        "ix_usage_entries_user_id_created_at", "usage_entries", ["user_id", "created_at"]
    )
    op.create_index("ix_usage_entries_month_state", "usage_entries", ["month", "state"])


def downgrade() -> None:
    op.drop_index("ix_usage_entries_month_state", table_name="usage_entries")
    op.drop_index("ix_usage_entries_user_id_created_at", table_name="usage_entries")
    op.drop_table("usage_entries")
    op.drop_index("ix_help_requests_session_item_id", table_name="help_requests")
    op.drop_index("ix_help_requests_user_id", table_name="help_requests")
    op.drop_table("help_requests")
    op.drop_table("item_help_state")
    # Native DROP COLUMN, not a batch rebuild: rebuilding "users" would DROP TABLE a table that
    # study_sessions and web_sessions reference, which fails with foreign keys enforced.
    op.execute("ALTER TABLE users DROP COLUMN privacy_epoch")
