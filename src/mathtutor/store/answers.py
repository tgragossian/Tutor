"""Every query over ``answers``. Attempt order is ``attempt_no``, oldest first (spec D8).

Only applied answers changed anything for the student, so only they are attempts here.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import ColumnElement, CursorResult, func, select, update
from sqlalchemy.orm import Session

from mathtutor.domain import VerdictStatus
from mathtutor.store.models import Answer


def _applied(session_item_id: int) -> ColumnElement[bool]:
    return (Answer.session_item_id == session_item_id) & Answer.applied.is_(True)


def applied_answers(db: Session, session_item_id: int) -> list[Answer]:
    """The presentation's applied answers, oldest attempt first."""
    rows = db.scalars(select(Answer).where(_applied(session_item_id)).order_by(Answer.attempt_no))
    return list(rows)


def latest_applied(db: Session, session_item_id: int) -> Answer | None:
    return db.scalar(
        select(Answer).where(_applied(session_item_id)).order_by(Answer.attempt_no.desc()).limit(1)
    )


def latest_wrong(db: Session, session_item_id: int) -> Answer | None:
    """The latest applied incorrect answer, if any."""
    return db.scalar(
        select(Answer)
        .where(_applied(session_item_id), Answer.status == VerdictStatus.INCORRECT)
        .order_by(Answer.attempt_no.desc())
        .limit(1)
    )


def next_attempt_no(db: Session, session_item_id: int) -> int:
    """The number the next applied answer takes: 1, then max + 1."""
    top = db.scalar(
        select(func.max(Answer.attempt_no)).where(Answer.session_item_id == session_item_id)
    )
    return (top or 0) + 1


def mistake_counts(db: Session, session_item_id: int) -> dict[str, int]:
    """Applied incorrect answers per mistake type; unlabeled ones are not counted."""
    rows = db.execute(
        select(Answer.mistake_type, func.count())
        .where(
            _applied(session_item_id),
            Answer.status == VerdictStatus.INCORRECT,
            Answer.mistake_type.is_not(None),
        )
        .group_by(Answer.mistake_type)
    ).all()
    return {mistake: n for mistake, n in rows if mistake is not None}


def set_mistake_type(db: Session, answer_id: int, mistake_type: str) -> bool:
    """Label an applied incorrect answer once (spec D4): the first writer wins. True if this
    call wrote the label."""
    written = db.execute(
        update(Answer)
        .where(
            Answer.id == answer_id,
            Answer.applied.is_(True),
            Answer.status == VerdictStatus.INCORRECT,
            Answer.mistake_type.is_(None),
        )
        .values(mistake_type=mistake_type)
        .execution_options(synchronize_session=False)
    )
    return cast(CursorResult[Any], written).rowcount == 1
