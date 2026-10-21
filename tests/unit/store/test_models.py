from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mathtutor.domain import Action, AnswerKind, ItemState, Method, VerdictReason, VerdictStatus
from mathtutor.store.models import (
    AttemptResult,
    ItemEvent,
    SessionItem,
    StudySession,
    Submission,
    User,
    WebSession,
)

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def _user(db: Session, name: str = "alice") -> User:
    user = User(username=name, password_hash="argon2-hash", created_at=NOW)
    db.add(user)
    db.flush()
    return user


def _item(db: Session) -> SessionItem:
    user = _user(db)
    study = StudySession(
        user_id=user.id, mode="practice", topics=["derivatives.basic_rules"], started_at=NOW
    )
    db.add(study)
    db.flush()
    item = SessionItem(
        session_id=study.id,
        item_id="d.power.01",
        content_version="0123456789ab",
        sequence=1,
        state=ItemState.ACTIVE,
        revision=0,
        served_at=NOW,
        tries_used=0,
    )
    db.add(item)
    db.flush()
    return item


def _submission(item: SessionItem, submission_id: str) -> Submission:
    return Submission(
        submission_id=submission_id,
        session_item_id=item.id,
        answer_kind=AnswerKind.EXPRESSION,
        answer_json='["Multiply", 2, "x"]',
        answer_latex="2x",
        created_at=NOW,
    )


def _result(submission: Submission) -> AttemptResult:
    return AttemptResult(
        submission_pk=submission.id,
        status=VerdictStatus.CORRECT,
        reason=VerdictReason.PROVEN,
        method=Method.SYMBOLIC,
        verifier_version="0.1.0+dev",
        worker_ms=12,
        queue_ms=0,
        seconds_on_item=30,
        counts_as_try=False,
        applied=True,
    )


def test_round_trip_all_models(db: Session) -> None:
    item = _item(db)
    sub = _submission(item, "11111111-1111-4111-8111-111111111111")
    db.add(sub)
    db.flush()
    db.add(_result(sub))
    db.add(ItemEvent(session_item_id=item.id, kind=Action.SKIP, created_at=NOW))
    db.add(
        WebSession(
            token_hash="a" * 64,
            user_id=item.session.user_id,
            csrf_token="csrf",
            created_at=NOW,
            expires_at=NOW + timedelta(days=7),
        )
    )
    db.commit()
    db.expire_all()
    loaded = db.get(SessionItem, item.id)
    assert loaded is not None
    assert loaded.state is ItemState.ACTIVE
    assert loaded.served_at == NOW
    assert loaded.session.topics == ["derivatives.basic_rules"]
    assert loaded.submissions[0].result is not None
    assert loaded.submissions[0].result.reason is VerdictReason.PROVEN
    assert loaded.submissions[0].result.applied is True


def test_submission_id_unique(db: Session) -> None:
    item = _item(db)
    db.add(_submission(item, "dup"))
    db.flush()
    db.add(_submission(item, "dup"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_username_unique(db: Session) -> None:
    _user(db, "bob")
    with pytest.raises(IntegrityError):
        _user(db, "bob")


def test_attempt_result_one_per_submission(db: Session) -> None:
    item = _item(db)
    sub = _submission(item, "s1")
    db.add(sub)
    db.flush()
    db.add(_result(sub))
    db.flush()
    db.add(_result(sub))
    with pytest.raises(IntegrityError):
        db.flush()


def test_session_item_sequence_unique(db: Session) -> None:
    item = _item(db)
    twin = SessionItem(
        session_id=item.session_id,
        item_id="d.power.02",
        content_version="0123456789ab",
        sequence=item.sequence,
        state=ItemState.ACTIVE,
        revision=0,
        served_at=NOW,
        tries_used=0,
    )
    db.add(twin)
    with pytest.raises(IntegrityError):
        db.flush()


def test_foreign_keys_enforced(db: Session) -> None:
    db.add(
        SessionItem(
            session_id=999,
            item_id="d.power.01",
            content_version="0123456789ab",
            sequence=1,
            state=ItemState.ACTIVE,
            revision=0,
            served_at=NOW,
            tries_used=0,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
