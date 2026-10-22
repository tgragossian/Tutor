"""Deterministic interleaving of a slow request, its duplicate and another user."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from unit.application.test_practice import ANSWER, BASIC, CORRECT, World

from mathtutor.application.errors import Busy
from mathtutor.store.models import AttemptResult, Submission
from mathtutor.verify.types import VerifierBusy


def test_br5_busy_duplicate_must_not_delete_another_inflight_reservation(tmp_path):
    w = World(tmp_path)
    try:
        alice_sid = w.svc.start_session(w.alice, [BASIC])
        alice_view = w.view(alice_sid)
        key = uuid4()
        bob_sid = w.svc.start_session(w.bob, [BASIC])
        bob_view = w.view(bob_sid, user=w.bob)
        bob_key = uuid4()

        def overlapping_requests():
            # Alice's original call is still in pool.submit, e.g. warming a replacement.
            w.clock.now += timedelta(seconds=11)
            w.pool.script.insert(0, VerifierBusy)
            with pytest.raises(Busy):
                w.svc.submit_answer(w.alice, alice_sid, key, alice_view.session_item_id, 0, ANSWER)
            # Bob finishes transaction A before Alice resumes transaction B.
            w.svc._reserve(w.bob, bob_sid, str(bob_key), bob_view.session_item_id, 0, ANSWER)

        w.pool.during = overlapping_requests
        w.submit(alice_sid, CORRECT, sid=key)
        with w.sessions() as db:
            attached_to = db.scalar(
                select(Submission.submission_id).join(
                    AttemptResult, AttemptResult.submission_pk == Submission.id
                )
            )
            assert attached_to == str(key), (
                "Alice's result attached to another submission",
                attached_to,
                str(bob_key),
            )
    finally:
        w.engine.dispose()
