"""Follow-up: two accepted recovery deviations, plus the remaining load-check gap."""

from datetime import timedelta
from uuid import uuid4

import pytest
from load import submit_burst
from unit.application.test_practice import ANSWER, BASIC, CORRECT, INCORRECT, World

from mathtutor.application.errors import StaleItem
from mathtutor.store.models import AttemptResult


def test_old_holder_replays_recoverys_result_without_a_second_transition(tmp_path):
    w = World(tmp_path)
    try:
        sid = w.svc.start_session(w.alice, [BASIC])
        item = w.view(sid).session_item_id
        key = uuid4()

        def recovery_finishes_first():
            w.clock.now += timedelta(seconds=11)
            w.pool.script.insert(0, CORRECT)
            w.svc.submit_answer(w.alice, sid, key, item, 0, ANSWER)

        w.pool.during = recovery_finishes_first
        result = w.submit(sid, INCORRECT, sid=key)
        assert result.replayed and result.outcome == CORRECT
        assert result.item.revision == 1 and result.item.tries_left == 3
        assert w.count(AttemptResult) == 1
    finally:
        w.engine.dispose()


def test_reused_integer_id_is_rejected_by_finalization(tmp_path):
    w = World(tmp_path)
    try:
        sid = w.svc.start_session(w.alice, [BASIC])
        item = w.view(sid).session_item_id
        old = w.svc._reserve(w.alice, sid, str(uuid4()), item, 0, ANSWER)
        w.svc._release(old)
        bob_sid = w.svc.start_session(w.bob, [BASIC])
        bob_item = w.view(bob_sid, user=w.bob).session_item_id
        new = w.svc._reserve(w.bob, bob_sid, str(uuid4()), bob_item, 0, ANSWER)
        assert new.submission_pk == old.submission_pk  # force the omitted safeguard's case
        w.pool.script.append(CORRECT)
        with pytest.raises(StaleItem):
            w.svc._grade(w.alice, sid, old)
        assert w.count(AttemptResult) == 0
        assert w.view(sid).revision == 0
        assert w.view(bob_sid, user=w.bob).revision == 0
    finally:
        w.engine.dispose()


def test_br4_real_verifier_internal_errors_must_fail_the_load_cli(monkeypatch):
    class CrashedVerifierClient:
        def __init__(self, base):
            pass

        def call(self, *args):
            return (
                200,
                {
                    "outcome": {
                        "status": "unable_to_verify",
                        "reason": "internal_error",
                        "method": "none",
                    }
                },
                [],
            )

    monkeypatch.setattr(submit_burst, "Client", CrashedVerifierClient)
    monkeypatch.setattr(submit_burst, "register", lambda *args: None)
    monkeypatch.setattr(
        submit_burst,
        "open_at_target",
        lambda *args: {"session_id": 1, "item": {"session_item_id": 1, "revision": 0}},
    )
    # Exercise the real threaded burst, outcome extraction, summary and CLI exit decision.
    assert submit_burst.main(["--base-url", "http://unused.invalid", "--users", "2"]) == 1
