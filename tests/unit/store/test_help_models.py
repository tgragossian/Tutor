from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mathtutor.domain import ItemState
from mathtutor.store.models import (
    HelpRequestRow,
    ItemHelpState,
    SessionItem,
    StudySession,
    UsageEntry,
    User,
)

NOW = datetime(2026, 10, 26, tzinfo=UTC)


def _item(db: Session) -> tuple[User, SessionItem]:
    user = User(username="u", password_hash="x", created_at=NOW)
    sess = StudySession(user=user, mode="practice", topics=[], started_at=NOW)
    item = SessionItem(
        session=sess,
        item_id="i",
        content_version="v",
        problem_json="{}",
        sequence=1,
        state=ItemState.ACTIVE,
        revision=0,
        served_at=NOW,
        tries_used=0,
    )
    db.add_all([user, sess, item])
    db.flush()
    return user, item


def _help(user: User, item: SessionItem, request_id: str) -> HelpRequestRow:
    return HelpRequestRow(
        request_id=request_id,
        user_id=user.id,
        session_item_id=item.id,
        item_revision=0,
        help_type="hint",
        payload_hash="h" * 64,
        privacy_epoch=0,
        help_seq=1,
        status="ok",
        prompt_version="p1",
        corpus_hash="c",
        index_fingerprint="f",
        retrieved_ids=[],
        cited_ids=[],
        guard_counts={},
        calls=1,
        created_at=NOW,
    )


def _usage(user_id: int, request_id: str) -> UsageEntry:
    return UsageEntry(
        request_id=request_id,
        user_id=user_id,
        kind="help",
        call_no=1,
        model="m",
        month="2026-10",
        state="reserved",
        reserved_micros=1000,
        input_tokens=0,
        output_tokens=0,
        created_at=NOW,
    )


def test_defaults(db: Session) -> None:
    user, item = _item(db)
    state = ItemHelpState(session_item_id=item.id)
    row = _help(user, item, "r" * 36)
    db.add_all([state, row])
    db.commit()
    assert (user.privacy_epoch, state.hint_level, state.help_seq) == (0, 1, 0)
    assert state.in_flight is None
    assert (row.arm, row.output_json, row.cleared_at) == ("none", None, None)


def test_request_id_unique(db: Session) -> None:
    user, item = _item(db)
    db.add(_help(user, item, "a" * 36))
    db.commit()
    db.add(_help(user, item, "a" * 36))
    with pytest.raises(IntegrityError):
        db.commit()


def test_usage_has_no_user_fk(db: Session) -> None:
    user, item = _item(db)
    db.add(_help(user, item, "b" * 36))
    db.add(_usage(user.id, "b" * 36))
    db.commit()
    db.execute(delete(HelpRequestRow))
    db.commit()
    assert db.scalars(select(UsageEntry)).one().user_id == user.id
    # A usage row for a user that does not exist is accepted: no foreign key.
    db.add(_usage(99999, "c" * 36))
    db.commit()
    assert len(db.scalars(select(UsageEntry)).all()) == 2
