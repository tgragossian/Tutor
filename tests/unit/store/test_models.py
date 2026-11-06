from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mathtutor.domain import Action, AnswerKind, ItemState, Method, VerdictReason, VerdictStatus
from mathtutor.store.models import (
    Answer,
    ItemEvent,
    SessionItem,
    StudySession,
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
        problem_json="{}",
        sequence=1,
        state=ItemState.ACTIVE,
        revision=0,
        served_at=NOW,
        tries_used=0,
    )
    db.add(item)
    db.flush()
    return item


def _answer(item: SessionItem, submission_id: str) -> Answer:
    return Answer(
        submission_id=submission_id,
        user_id=item.session.user_id,
        session_item_id=item.id,
        answer_kind=AnswerKind.EXPRESSION,
        mathjson=["Multiply", 2, "x"],
        latex="2x",
        created_at=NOW,
    )


def _grade(answer: Answer) -> None:
    answer.attempt_no = 1
    answer.status = VerdictStatus.CORRECT
    answer.reason = VerdictReason.PROVEN
    answer.method = Method.SYMBOLIC
    answer.verifier_version = "0.1.0+dev"
    answer.worker_ms = 12
    answer.queue_ms = 0
    answer.seconds_on_item = 30
    answer.counts_as_try = False
    answer.applied = True


def test_round_trip_all_models(db: Session) -> None:
    item = _item(db)
    answer = _answer(item, "11111111-1111-4111-8111-111111111111")
    _grade(answer)
    db.add(answer)
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
    stored = loaded.answers[0]
    assert stored.mathjson == ["Multiply", 2, "x"] and stored.choice_id is None
    assert stored.reason is VerdictReason.PROVEN
    assert (stored.applied, stored.attempt_no, stored.mistake_type) == (True, 1, None)


def test_submission_id_unique(db: Session) -> None:
    item = _item(db)
    db.add(_answer(item, "dup"))
    db.flush()
    db.add(_answer(item, "dup"))
    with pytest.raises(IntegrityError):
        db.flush()


def test_username_unique(db: Session) -> None:
    _user(db, "bob")
    with pytest.raises(IntegrityError):
        _user(db, "bob")


def test_ungraded_answer_has_null_verdict(db: Session) -> None:
    item = _item(db)
    db.add(_answer(item, "s1"))
    db.commit()
    db.expire_all()
    loaded = db.get(SessionItem, item.id)
    assert loaded is not None
    stored = loaded.answers[0]
    assert (stored.status, stored.applied, stored.attempt_no, stored.lease) == (None, None, None, 0)


def test_session_item_sequence_unique(db: Session) -> None:
    item = _item(db)
    twin = SessionItem(
        session_id=item.session_id,
        item_id="d.power.02",
        content_version="0123456789ab",
        problem_json="{}",
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
            problem_json="{}",
            sequence=1,
            state=ItemState.ACTIVE,
            revision=0,
            served_at=NOW,
            tries_used=0,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
