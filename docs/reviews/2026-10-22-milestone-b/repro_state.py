"""Review assertions of desired behavior; run explicitly, outside normal collection."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from unit.application.test_practice import ANSWER, BASIC, INCORRECT, World

from mathtutor.application.errors import StaleItem
from mathtutor.store.models import AttemptResult


@pytest.fixture
def world(tmp_path):
    w = World(tmp_path)
    try:
        yield w
    finally:
        w.engine.dispose()


def test_br2_orphan_must_keep_its_original_revision(world):
    w = world
    sid = w.svc.start_session(w.alice, [BASIC])
    initial = w.view(sid)
    key = uuid4()
    # Actual transaction A, followed by a simulated interruption before grading.
    w.svc._reserve(w.alice, sid, str(key), initial.session_item_id, 0, ANSWER)
    w.submit(sid, INCORRECT)  # another request wins revision 0
    current = w.view(sid)
    assert current.revision == 1 and current.tries_left == 2
    w.clock.now += timedelta(seconds=11)
    w.pool.script.append(INCORRECT)
    with pytest.raises(StaleItem):
        w.svc.submit_answer(w.alice, sid, key, initial.session_item_id, current.revision, ANSWER)
    assert w.view(sid).tries_left == 2


def test_br3_seconds_on_item_ends_at_submission(world):
    w = world
    sid = w.svc.start_session(w.alice, [BASIC])
    w.clock.now += timedelta(seconds=42)

    def grading_delay():
        w.clock.now += timedelta(seconds=7)

    w.pool.during = grading_delay
    w.submit(sid, INCORRECT)
    with w.sessions() as db:
        result = db.scalar(select(AttemptResult))
        assert result.seconds_on_item == 42, result.seconds_on_item
