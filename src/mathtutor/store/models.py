"""ORM tables for users, login sessions and practice state (spec 06, ruling R2)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Dialect,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from mathtutor.domain import Action, AnswerKind, ItemState, Method, VerdictReason, VerdictStatus


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC timestamps. SQLite drops the offset, so it is restored on load."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def _enum(cls: type[StrEnum]) -> Enum:
    """Store an enum as its string value; no CHECK constraint, so new values need no migration."""
    return Enum(
        cls,
        native_enum=False,
        create_constraint=False,
        length=32,
        values_callable=lambda members: [m.value for m in members],
    )


class Base(DeclarativeBase):
    type_annotation_map: dict[Any, Any] = {datetime: UTCDateTime()}


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime]
    # Bumped by "Clear history"; help requests started under an older epoch are discarded.
    privacy_epoch: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    study_sessions: Mapped[list[StudySession]] = relationship(back_populates="user")


class WebSession(Base):
    """Server-side login session (ruling R2): hashed token, CSRF token and expiry."""

    __tablename__ = "web_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]

    user: Mapped[User] = relationship()


class StudySession(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (Index("ix_study_sessions_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mode: Mapped[str] = mapped_column(String(16))
    topics: Mapped[list[str]] = mapped_column(JSON)
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    # Set by "Clear history": hidden from the list, but its answers still count for selection.
    hidden_at: Mapped[datetime | None]

    user: Mapped[User] = relationship(back_populates="study_sessions")
    items: Mapped[list[SessionItem]] = relationship(
        back_populates="session", order_by="SessionItem.sequence"
    )


class SessionItem(Base):
    """One presentation of a problem; showing it again creates a new row."""

    __tablename__ = "session_items"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence", name="uq_session_items_session_sequence"),
        Index("ix_session_items_session_id_state", "session_id", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("study_sessions.id"))
    item_id: Mapped[str] = mapped_column(String(128))
    content_version: Mapped[str] = mapped_column(String(12))
    # The problem as served (compiled JSON); views and grading use it, never newer content.
    problem_json: Mapped[str] = mapped_column(Text)
    sequence: Mapped[int] = mapped_column(Integer)
    state: Mapped[ItemState] = mapped_column(_enum(ItemState))
    revision: Mapped[int] = mapped_column(Integer)
    served_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    tries_used: Mapped[int] = mapped_column(Integer)

    session: Mapped[StudySession] = relationship(back_populates="items")
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="session_item", order_by="Submission.id"
    )
    events: Mapped[list[ItemEvent]] = relationship(
        back_populates="session_item", order_by="ItemEvent.id"
    )


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (Index("ix_submissions_session_item_id", "session_item_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[str] = mapped_column(String(36), unique=True)
    session_item_id: Mapped[int] = mapped_column(ForeignKey("session_items.id"))
    answer_kind: Mapped[AnswerKind] = mapped_column(_enum(AnswerKind))
    answer_json: Mapped[str] = mapped_column(Text)
    answer_latex: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    # The presentation revision this answer was reserved against (review B-R2). NULL only on
    # rows reserved before migration 0003; recovery never guesses it.
    reserved_revision: Mapped[int | None] = mapped_column(Integer)
    # Recovery lease (review B-R5): 0 while the original request owns the reservation; each
    # orphan recovery claims it by incrementing it. Only the holder may delete the row.
    lease: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    leased_at: Mapped[datetime | None]

    session_item: Mapped[SessionItem] = relationship(back_populates="submissions")
    result: Mapped[AttemptResult | None] = relationship(back_populates="submission")


class AttemptResult(Base):
    __tablename__ = "attempt_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_pk: Mapped[int] = mapped_column(ForeignKey("submissions.id"), unique=True)
    status: Mapped[VerdictStatus] = mapped_column(_enum(VerdictStatus))
    reason: Mapped[VerdictReason] = mapped_column(_enum(VerdictReason))
    method: Mapped[Method] = mapped_column(_enum(Method))
    verifier_version: Mapped[str] = mapped_column(String(64))
    worker_ms: Mapped[int] = mapped_column(Integer)
    queue_ms: Mapped[int] = mapped_column(Integer)
    seconds_on_item: Mapped[int] = mapped_column(Integer)
    counts_as_try: Mapped[bool] = mapped_column(Boolean)
    # False when the presentation changed while grading (spec 06 step 4): stored, not applied.
    applied: Mapped[bool] = mapped_column(Boolean)

    submission: Mapped[Submission] = relationship(back_populates="result")


class ItemHelpState(Base):
    """Per-presentation help counters and the single in-flight help request id.

    ``hint_level`` (1-3) is the next hint's level once the item has a wrong answer (level 0,
    "how to start", is used while it has none). ``hint_attempt_pk`` is the latest wrong
    submission the last delivered hint addressed (ruling R35)."""

    __tablename__ = "item_help_state"

    session_item_id: Mapped[int] = mapped_column(ForeignKey("session_items.id"), primary_key=True)
    hint_level: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    hint_attempt_pk: Mapped[int | None] = mapped_column(Integer)
    help_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    in_flight: Mapped[str | None] = mapped_column(String(36))


class HelpRequestRow(Base):
    """One help request. Only ``output_json`` holds model text; the rest is metadata."""

    __tablename__ = "help_requests"
    __table_args__ = (
        Index("ix_help_requests_user_id", "user_id"),
        Index("ix_help_requests_session_item_id", "session_item_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    session_item_id: Mapped[int] = mapped_column(ForeignKey("session_items.id"))
    item_revision: Mapped[int] = mapped_column(Integer)
    help_type: Mapped[str] = mapped_column(String(32))
    confusion_id: Mapped[str | None] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    privacy_epoch: Mapped[int] = mapped_column(Integer)
    help_seq: Mapped[int] = mapped_column(Integer)
    hint_level: Mapped[int | None] = mapped_column(Integer)  # the level written (0-3)
    hint_mistake: Mapped[str | None] = mapped_column(String(8))  # "same" / "new" (R35)
    status: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str | None] = mapped_column(String(32))
    model: Mapped[str | None] = mapped_column(String(64))
    prompt_version: Mapped[str] = mapped_column(String(32))
    corpus_hash: Mapped[str] = mapped_column(String(64))
    index_fingerprint: Mapped[str] = mapped_column(String(64))
    retrieved_ids: Mapped[list[str]] = mapped_column(JSON)
    cited_ids: Mapped[list[str]] = mapped_column(JSON)
    guard_counts: Mapped[dict[str, int]] = mapped_column(JSON)
    calls: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    arm: Mapped[str] = mapped_column(String(16), default="none", server_default="none")
    serving_model: Mapped[str | None] = mapped_column(String(64))
    output_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    cleared_at: Mapped[datetime | None]
    next_submission_id: Mapped[str | None] = mapped_column(String(36))


class UsageEntry(Base):
    """Durable spend ledger. ``user_id`` has no foreign key: spend outlives users and help rows."""

    __tablename__ = "usage_entries"
    __table_args__ = (
        UniqueConstraint("request_id", "call_no", name="uq_usage_entries_request_call"),
        Index("ix_usage_entries_user_id_created_at", "user_id", "created_at"),
        Index("ix_usage_entries_month_state", "month", "state"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16))  # "help" | "eval"
    call_no: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(64))
    month: Mapped[str] = mapped_column(String(7))  # UTC "YYYY-MM"
    state: Mapped[str] = mapped_column(String(16))  # "reserved" | "settled" | "uncertain"
    reserved_micros: Mapped[int] = mapped_column(Integer)
    settled_micros: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime]
    settled_at: Mapped[datetime | None]


class ItemEvent(Base):
    """``reveal``, ``skip`` or ``advance`` on a presentation. Answers are never edited."""

    __tablename__ = "item_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_item_id: Mapped[int] = mapped_column(ForeignKey("session_items.id"))
    kind: Mapped[Action] = mapped_column(_enum(Action))
    created_at: Mapped[datetime]

    session_item: Mapped[SessionItem] = relationship(back_populates="events")
