"""Orphaned-reservation recovery (review 2026-10-22, B-R5 / B-R2 / B-R3).

An aged reservation is not proof its owner died: the original request may still be grading.
Recovery claims a lease, uses the revision stored at reservation time, and only the lease
holder may delete a reservation. Results are stored only against the row they were made for.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from unit.application.test_practice import ANSWER, BASIC, CORRECT, INCORRECT, World

from mathtutor.application.errors import Busy, StaleItem, SubmissionPending
from mathtutor.domain import AnswerKind, FormatIssueCode, ItemState
from mathtutor.store.models import AttemptResult, Submission
from mathtutor.verify.types import FormatIssue, VerifierBusy


@pytest.fixture
def w(tmp_path: Path) -> Iterator[World]:
    world = World(tmp_path)
    try:
        yield world
    finally:
        world.engine.dispose()


def _orphan(w: World, sid: int, revision: int | None) -> uuid.UUID:
    """A reservation left by a crash between transactions A and B."""
    v = w.view(sid)
    key = uuid.uuid4()
    with w.sessions.begin() as db:
        db.add(
            Submission(
                submission_id=str(key),
                session_item_id=v.session_item_id,
                answer_kind=AnswerKind.EXPRESSION,
                answer_json='{"mathjson": ["Multiply", 2, "x"], "choice_id": null}',
                answer_latex="2x",
                created_at=w.clock.now,
                reserved_revision=revision,
            )
        )
    return key


def test_busy_duplicate_does_not_delete_a_live_reservation(w: World) -> None:
    """B-R5: Alice's result must stay attached to Alice's submission."""
    alice_sid = w.svc.start_session(w.alice, [BASIC])
    alice_view = w.view(alice_sid)
    key = uuid.uuid4()
    bob_sid = w.svc.start_session(w.bob, [BASIC])
    bob_view = w.view(bob_sid, user=w.bob)
    bob_key = uuid.uuid4()

    def overlapping_requests() -> None:
        w.clock.now += timedelta(seconds=11)  # Alice is still in pool.submit
        w.pool.script.insert(0, VerifierBusy)
        with pytest.raises(Busy):
            w.svc.submit_answer(w.alice, alice_sid, key, alice_view.session_item_id, 0, ANSWER)
        w.svc._reserve(w.bob, bob_sid, str(bob_key), bob_view.session_item_id, 0, ANSWER)

    w.pool.during = overlapping_requests
    r = w.submit(alice_sid, CORRECT, sid=key)
    assert r.outcome == CORRECT
    with w.sessions() as db:
        rows = db.execute(
            select(Submission.submission_id, AttemptResult.status).join(
                AttemptResult, AttemptResult.submission_pk == Submission.id
            )
        ).all()
        assert [row[0] for row in rows] == [str(key)]
        bob = db.scalar(select(Submission).where(Submission.submission_id == str(bob_key)))
        assert bob is not None and bob.result is None


def test_recovery_holds_a_lease_so_a_second_recovery_waits(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    key = _orphan(w, sid, revision=0)
    w.clock.now += timedelta(seconds=11)
    item = w.view(sid).session_item_id

    def second_recovery() -> None:
        with pytest.raises(SubmissionPending):
            w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)

    w.pool.during = second_recovery
    w.pool.script.append(CORRECT)
    r = w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)
    assert r.outcome == CORRECT
    assert w.count(AttemptResult) == 1 and len(w.pool.requests) == 1


def test_busy_recovery_keeps_the_reservation_for_a_later_retry(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    key = _orphan(w, sid, revision=0)
    item = w.view(sid).session_item_id
    w.clock.now += timedelta(seconds=11)
    w.pool.script.append(VerifierBusy)
    with pytest.raises(Busy):
        w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)
    assert w.count(Submission) == 1
    with pytest.raises(SubmissionPending):  # the lease is fresh again
        w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)
    w.clock.now += timedelta(seconds=11)
    w.pool.script.append(INCORRECT)
    assert w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER).outcome == INCORRECT
    assert w.count(AttemptResult) == 1


def test_format_issue_on_recovery_removes_the_reservation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    key = _orphan(w, sid, revision=0)
    item = w.view(sid).session_item_id
    w.clock.now += timedelta(seconds=11)
    issue = FormatIssue(FormatIssueCode.INCOMPLETE, "")
    w.pool.script.append(issue)
    assert w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER).outcome == issue
    assert w.count(Submission) == 0 and w.view(sid).tries_left == 3


def test_original_owner_busy_after_recovery_claimed_does_not_delete(w: World) -> None:
    """The original request may only delete while it still holds the lease."""
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    key = uuid.uuid4()

    def recovery_claims_and_finishes() -> None:
        w.clock.now += timedelta(seconds=11)
        w.pool.script.insert(0, CORRECT)
        w.svc.submit_answer(w.alice, sid, key, v.session_item_id, 0, ANSWER)
        w.pool.script.insert(0, VerifierBusy)  # what the original request then gets

    w.pool.during = recovery_claims_and_finishes
    with pytest.raises(Busy):
        w.svc.submit_answer(w.alice, sid, key, v.session_item_id, 0, ANSWER)
    assert w.count(Submission) == 1 and w.count(AttemptResult) == 1


def test_orphan_keeps_its_original_revision(w: World) -> None:
    """B-R2: a retry naming a newer revision cannot revive an answer that lost the race."""
    sid = w.svc.start_session(w.alice, [BASIC])
    initial = w.view(sid)
    key = uuid.uuid4()
    w.svc._reserve(w.alice, sid, str(key), initial.session_item_id, 0, ANSWER)
    w.submit(sid, INCORRECT)  # another request wins revision 0
    current = w.view(sid)
    assert (current.revision, current.tries_left) == (1, 2)
    w.clock.now += timedelta(seconds=11)
    w.pool.script.append(INCORRECT)
    with pytest.raises(StaleItem):
        w.svc.submit_answer(w.alice, sid, key, initial.session_item_id, current.revision, ANSWER)
    assert w.view(sid).tries_left == 2


def test_orphan_with_its_original_revision_still_recovers(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    key = _orphan(w, sid, revision=0)
    w.clock.now += timedelta(seconds=11)
    w.pool.script.append(CORRECT)
    item = w.view(sid).session_item_id
    r = w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)
    assert r.outcome == CORRECT and r.item.state is ItemState.ANSWERED


def test_pre_migration_orphan_without_a_revision_is_dropped_as_stale(w: World) -> None:
    """Rows reserved before migration 0003 have no stored revision: never guess one."""
    sid = w.svc.start_session(w.alice, [BASIC])
    key = _orphan(w, sid, revision=None)
    w.clock.now += timedelta(seconds=11)
    item = w.view(sid).session_item_id
    with pytest.raises(StaleItem):
        w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)
    assert w.count(Submission) == 0 and w.pool.requests == []
    assert w.view(sid).tries_left == 3


def test_seconds_on_item_ends_at_submission(w: World) -> None:
    """B-R3: grading time is not the student's time."""
    sid = w.svc.start_session(w.alice, [BASIC])
    w.clock.now += timedelta(seconds=42)

    def grading_delay() -> None:
        w.clock.now += timedelta(seconds=7)

    w.pool.during = grading_delay
    w.submit(sid, INCORRECT)
    with w.sessions() as db:
        result = db.scalar(select(AttemptResult))
        assert result is not None and result.seconds_on_item == 42


def test_recovered_answer_keeps_its_original_answer_time(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    w.clock.now += timedelta(seconds=30)
    key = _orphan(w, sid, revision=0)
    w.clock.now += timedelta(minutes=5)
    w.pool.script.append(INCORRECT)
    w.svc.submit_answer(w.alice, sid, key, w.view(sid).session_item_id, 0, ANSWER)
    with w.sessions() as db:
        result = db.scalar(select(AttemptResult))
        assert result is not None and result.seconds_on_item == 30
