"""Answer queries in ``store/answers.py``: attempt order, numbering and write-once labels."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mathtutor.domain import AnswerKind, ItemState, Method, VerdictReason, VerdictStatus
from mathtutor.store.answers import (
    applied_answers,
    latest_applied,
    latest_wrong,
    mistake_counts,
    next_attempt_no,
    set_mistake_type,
)
from mathtutor.store.models import Answer, SessionItem, StudySession, User

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
RIGHT, WRONG = VerdictStatus.CORRECT, VerdictStatus.INCORRECT
UNSURE = VerdictStatus.UNABLE_TO_VERIFY


def _item(db: Session) -> SessionItem:
    user = User(username="ann", password_hash="x", created_at=NOW)
    study = StudySession(user=user, mode="practice", topics=[], started_at=NOW)
    item = SessionItem(
        session=study,
        item_id="i",
        content_version="v",
        problem_json="{}",
        sequence=1,
        state=ItemState.ACTIVE,
        revision=0,
        served_at=NOW,
        tries_used=0,
    )
    db.add_all([user, study, item])
    db.flush()
    return item


def _answer(
    db: Session,
    item: SessionItem,
    status: VerdictStatus | None,
    attempt_no: int | None,
    *,
    applied: bool = True,
    mistake_type: str | None = None,
) -> Answer:
    graded = status is not None
    row = Answer(
        submission_id=str(uuid.uuid4()),
        user_id=item.session.user_id,
        session_item_id=item.id,
        attempt_no=attempt_no,
        answer_kind=AnswerKind.EXPRESSION,
        mathjson=["Multiply", 2, "x"],
        latex="2x",
        created_at=NOW,
        reserved_revision=0,
        status=status,
        reason=VerdictReason.PROVEN if graded else None,
        method=Method.SYMBOLIC if graded else None,
        verifier_version="v" if graded else None,
        worker_ms=1 if graded else None,
        queue_ms=0 if graded else None,
        seconds_on_item=5 if graded else None,
        counts_as_try=(applied and status is WRONG) if graded else None,
        applied=applied if graded else None,
        mistake_type=mistake_type,
    )
    db.add(row)
    db.flush()
    return row


def test_applied_answers_in_attempt_order(db: Session) -> None:
    item = _item(db)
    second = _answer(db, item, RIGHT, 2)
    _answer(db, item, WRONG, None, applied=False)
    first = _answer(db, item, WRONG, 1)
    _answer(db, item, None, None)  # reserved, ungraded
    assert [a.id for a in applied_answers(db, item.id)] == [first.id, second.id]
    assert latest_applied(db, item.id) == second


def test_latest_wrong_skips_correct_and_unapplied(db: Session) -> None:
    item = _item(db)
    assert latest_wrong(db, item.id) is None
    wrong = _answer(db, item, WRONG, 1)
    _answer(db, item, UNSURE, 2)
    _answer(db, item, WRONG, None, applied=False)
    _answer(db, item, RIGHT, 3)
    assert latest_wrong(db, item.id) == wrong


def test_next_attempt_no_starts_at_1_and_skips_unapplied(db: Session) -> None:
    item = _item(db)
    assert next_attempt_no(db, item.id) == 1
    _answer(db, item, WRONG, 1)
    _answer(db, item, WRONG, None, applied=False)
    _answer(db, item, None, None)
    assert next_attempt_no(db, item.id) == 2


def test_attempt_no_unique_per_item(db: Session) -> None:
    item = _item(db)
    _answer(db, item, WRONG, 1)
    with pytest.raises(IntegrityError):
        _answer(db, item, RIGHT, 1)


def test_set_mistake_type_is_write_once(db: Session) -> None:
    item = _item(db)
    wrong = _answer(db, item, WRONG, 1)
    assert set_mistake_type(db, wrong.id, "algebra") is True
    assert set_mistake_type(db, wrong.id, "wrong_rule") is False
    db.refresh(wrong)
    assert wrong.mistake_type == "algebra"


def test_set_mistake_type_refuses_correct_answer(db: Session) -> None:
    item = _item(db)
    right = _answer(db, item, RIGHT, 1)
    stale = _answer(db, item, WRONG, None, applied=False)
    assert set_mistake_type(db, right.id, "algebra") is False
    assert set_mistake_type(db, stale.id, "algebra") is False
    db.refresh(right)
    assert right.mistake_type is None


def test_mistake_counts_ignores_unlabeled(db: Session) -> None:
    item = _item(db)
    _answer(db, item, WRONG, 1, mistake_type="algebra")
    _answer(db, item, WRONG, 2)
    _answer(db, item, WRONG, 3, mistake_type="algebra")
    _answer(db, item, WRONG, 4, mistake_type="incomplete")
    _answer(db, item, WRONG, None, applied=False, mistake_type="wrong_rule")
    assert mistake_counts(db, item.id) == {"algebra": 2, "incomplete": 1}
