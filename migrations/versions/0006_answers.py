"""One ``answers`` row per answer, replacing ``submissions`` + ``attempt_results`` (spec D1-D3).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05

Ids are kept (``answers.id`` = ``submissions.id``). ``answer_json`` splits into ``mathjson``
and ``choice_id``; ``answer_latex`` becomes ``latex``; ``user_id`` comes from the session.
``attempt_no`` numbers applied answers 1, 2, ... per presentation in id order; unapplied
results, orphan reservations (no result) and NULL ``reserved_revision`` rows are copied as
they are with no number. ``mistake_type`` is the R35 ``hint_type`` of the wrong answer the
last hint addressed. Values are copied raw (no type processing), so timestamps keep their
stored text. The downgrade rebuilds both tables; ``attempt_results.id`` is renumbered in
answer order, and ``user_id``, ``attempt_no`` and ``mistake_type`` are dropped.
"""

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

from mathtutor.jsonio import loads_exact

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TYPED = ("submission_id", "session_item_id", "answer_kind", "created_at")
_LEASE = ("reserved_revision", "lease", "leased_at")
_VERDICT = (
    "status",
    "reason",
    "method",
    "verifier_version",
    "worker_ms",
    "queue_ms",
    "seconds_on_item",
    "counts_as_try",
    "applied",
)
_ANSWER_COLS = (
    ("id", "user_id", "attempt_no", "mathjson", "choice_id", "latex", "mistake_type")
    + _TYPED
    + _LEASE
    + _VERDICT
)


def _raw_table(name: str, cols: Sequence[str]) -> sa.TableClause:
    """Untyped columns: values pass through exactly as SQLite stored them."""
    return sa.table(name, *(sa.column(c) for c in cols))


def _insert(name: str, rows: list[dict[str, Any]]) -> None:
    if rows:
        op.get_bind().execute(sa.insert(_raw_table(name, list(rows[0]))), rows)


def _json_text(value: Any) -> str | None:
    return None if value is None else json.dumps(value)


def upgrade() -> None:
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=True),
        sa.Column("answer_kind", sa.String(length=32), nullable=False),
        sa.Column("mathjson", sa.Text(), nullable=True),  # TEXT affinity keeps numbers exact
        sa.Column("choice_id", sa.String(length=64), nullable=True),
        sa.Column("latex", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_revision", sa.Integer(), nullable=True),
        sa.Column("lease", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("verifier_version", sa.String(length=64), nullable=True),
        sa.Column("worker_ms", sa.Integer(), nullable=True),
        sa.Column("queue_ms", sa.Integer(), nullable=True),
        sa.Column("seconds_on_item", sa.Integer(), nullable=True),
        sa.Column("counts_as_try", sa.Boolean(), nullable=True),
        sa.Column("applied", sa.Boolean(), nullable=True),
        sa.Column("mistake_type", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["session_item_id"], ["session_items.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_item_id", "attempt_no", name="uq_answers_item_attempt"),
        sa.UniqueConstraint("submission_id"),
    )
    with op.batch_alter_table("answers", schema=None) as batch_op:
        batch_op.create_index("ix_answers_session_item_id", ["session_item_id"], unique=False)
        batch_op.create_index(
            "ix_answers_user_id_mistake_type", ["user_id", "mistake_type"], unique=False
        )

    bind = op.get_bind()
    labeled = {
        pk: kind
        for pk, kind in bind.execute(
            sa.text(
                "SELECT hint_attempt_pk, hint_type FROM item_help_state"
                " WHERE hint_attempt_pk IS NOT NULL AND hint_type IS NOT NULL"
            )
        )
    }
    old = bind.execute(
        sa.text(
            "SELECT s.id, ss.user_id, s.answer_json, s.answer_latex, "
            + ", ".join(f"s.{c}" for c in _TYPED + _LEASE)
            + ", "
            + ", ".join(f"r.{c}" for c in _VERDICT)
            + " FROM submissions s"
            " JOIN session_items si ON si.id = s.session_item_id"
            " JOIN study_sessions ss ON ss.id = si.session_id"
            " LEFT JOIN attempt_results r ON r.submission_pk = s.id"
            " ORDER BY s.id"
        )
    ).mappings()
    numbered: dict[int, int] = {}
    rows: list[dict[str, Any]] = []
    for row in old:
        data = loads_exact(row["answer_json"])
        attempt_no = mistake_type = None
        if row["applied"]:
            attempt_no = numbered[row["session_item_id"]] = (
                numbered.get(row["session_item_id"], 0) + 1
            )
            if row["status"] == "incorrect":
                mistake_type = labeled.get(row["id"])
        rows.append(
            {c: row[c] for c in ("id", "user_id") + _TYPED + _LEASE + _VERDICT}
            | {
                "attempt_no": attempt_no,
                "mathjson": _json_text(data.get("mathjson")),
                "choice_id": data.get("choice_id"),
                "latex": row["answer_latex"],
                "mistake_type": mistake_type,
            }
        )
    _insert("answers", rows)
    op.drop_table("attempt_results")
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index("ix_submissions_session_item_id")
    op.drop_table("submissions")


def downgrade() -> None:
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("session_item_id", sa.Integer(), nullable=False),
        sa.Column("answer_kind", sa.String(length=32), nullable=False),
        sa.Column("answer_json", sa.Text(), nullable=False),
        sa.Column("answer_latex", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_revision", sa.Integer(), nullable=True),
        sa.Column("lease", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leased_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_item_id"], ["session_items.id"]),
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
        sa.Column("applied", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["submission_pk"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_pk"),
    )

    bind = op.get_bind()
    answers = bind.execute(
        sa.select(_raw_table("answers", _ANSWER_COLS)).order_by(sa.column("id"))
    ).mappings()
    submissions: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for row in answers:
        mathjson = None if row["mathjson"] is None else loads_exact(row["mathjson"])
        submissions.append(
            {c: row[c] for c in ("id",) + _TYPED + _LEASE}
            | {
                "answer_json": json.dumps({"mathjson": mathjson, "choice_id": row["choice_id"]}),
                "answer_latex": row["latex"],
            }
        )
        if row["status"] is not None:
            results.append({"submission_pk": row["id"]} | {c: row[c] for c in _VERDICT})
    _insert("submissions", submissions)
    _insert("attempt_results", results)
    with op.batch_alter_table("answers", schema=None) as batch_op:
        batch_op.drop_index("ix_answers_user_id_mistake_type")
        batch_op.drop_index("ix_answers_session_item_id")
    op.drop_table("answers")
