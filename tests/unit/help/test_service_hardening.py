"""Task 11 fix round 1: billed-call accounting, replay hardening, finalize failures."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy.orm import Session
from support.helpkit import CFG, Kit, make_kit, output

from mathtutor.application.errors import DatabaseBusy
from mathtutor.help import messages
from mathtutor.help.generator import GenerationResult
from mathtutor.help.render import render_help_html
from mathtutor.help.service import HelpIn, HelpService, HelpStatus

STUCK_S = CFG.admission.uncertain_after_s + 1
PROBE = ["See $\x00$ 18x times stuff $\x00$ ok", "See $\x00$ words $\x00$ ok"]


@pytest.fixture
def kit(tmp_path: Path) -> Kit:
    return make_kit(tmp_path)


def _boom(*_a: object, **_k: object) -> object:
    raise RuntimeError("guard crashed")


def test_guard_crash_settles_real_tokens(kit: Kit) -> None:
    kit.svc._pipeline._guard.check = _boom  # type: ignore[method-assign]
    kit.generator.script = [output(tokens=(2000, 300))]
    out = kit.help()
    assert out.status is HelpStatus.UNAVAILABLE
    (entry,) = kit.usage()
    assert entry.state == "settled"
    assert (entry.input_tokens, entry.output_tokens) == (2000, 300)
    assert entry.settled_micros and entry.settled_micros > 0
    assert kit.rows()[0].calls == 1


def test_guard_crash_without_usage_is_uncertain(kit: Kit) -> None:
    kit.svc._pipeline._guard.check = _boom  # type: ignore[method-assign]
    good = output()
    kit.generator.script = [GenerationResult(good.text, "end_turn", None, None, CFG.model, None, 5)]
    assert kit.help().status is HelpStatus.UNAVAILABLE
    assert kit.usage()[0].state == "uncertain"


@pytest.mark.parametrize("text", PROBE)
def test_control_characters_are_invalid_output(kit: Kit, text: str) -> None:
    kit.generator.script = [output(text), output(text)]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.FALLBACK and "\x00" not in (out.html or "")
    assert kit.row(rid).reason == "invalid_control_char"
    assert kit.guard_pool.requests == []  # rejected before the guard


def _disabled(kit: Kit) -> HelpService:
    return HelpService(
        kit.sessions,
        CFG,
        kit.ledger,
        kit.svc._pipeline,
        kit.grade_pool,
        {},
        clock=kit.clock,
        now=kit.wall,
        enabled=False,
    )


def test_replay_served_when_disabled_or_busy(kit: Kit) -> None:
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    first = kit.help(rid=rid)
    assert first.status is HelpStatus.DELIVERED
    req = HelpIn(rid, kit.item.session_item_id, kit.item.revision, "hint", None)
    assert _disabled(kit).request_help(kit.user, req) == first
    held = [kit.svc._slots.acquire(blocking=False) for _ in range(CFG.admission.concurrency)]
    assert all(held)
    assert kit.svc.request_help(kit.user, req) == first
    # New work still needs a slot.
    assert kit.help().status is HelpStatus.UNAVAILABLE
    for _ in held:
        kit.svc._slots.release()


def test_replay_of_old_pending_is_abandoned(kit: Kit) -> None:
    rid = uuid.uuid4()
    replays: list[object] = []

    def stuck(_req: object) -> None:
        kit.generator.before = None
        replays.append(kit.help(rid=rid))  # still young: pending
        kit.wall.advance(seconds=STUCK_S)
        replays.append(kit.help(rid=rid))  # older than 120 s: abandoned

    kit.generator.script = [output()]
    kit.generator.before = stuck
    late = kit.help(rid=rid)
    young, old = replays
    assert young.status is HelpStatus.PENDING  # type: ignore[attr-defined]
    assert old.status is HelpStatus.UNAVAILABLE  # type: ignore[attr-defined]
    assert old.html == render_help_html(messages.UNAVAILABLE)  # type: ignore[attr-defined]
    assert late.status is HelpStatus.STALE and late.html is None
    assert kit.help(rid=rid).status is HelpStatus.UNAVAILABLE


def test_late_finish_without_newer_request_is_stale(kit: Kit) -> None:
    def slow(_req: object) -> None:
        kit.wall.advance(seconds=STUCK_S)

    kit.generator.script = [output()]
    kit.generator.before = slow
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.STALE and out.html is None
    row = kit.row(rid)
    assert (row.status, row.reason, row.output_json) == ("unavailable", "abandoned", None)
    state = kit.state()
    assert state is not None and (state.hint_level, state.help_seq, state.in_flight) == (1, 0, None)
    assert kit.usage()[0].state == "settled"
    kit.generator.before = None
    kit.generator.script = [output()]
    assert kit.help().status is HelpStatus.DELIVERED


def _flaky_tx(kit: Kit, busy: set[int]) -> dict[str, int]:
    """Make the service's write transactions number ``busy`` raise ``DatabaseBusy``."""
    real = kit.svc._tx
    calls = {"n": 0}

    @contextmanager
    def flaky() -> Iterator[Session]:
        calls["n"] += 1
        if calls["n"] in busy:
            raise DatabaseBusy("busy")
        with real() as db:
            yield db

    kit.svc._tx = flaky  # type: ignore[method-assign]
    return calls


def test_finalize_retried_once_on_busy_db(kit: Kit) -> None:
    calls = _flaky_tx(kit, {2})  # admission is 1, finalization is 2, its retry is 3
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.DELIVERED and calls["n"] == 3
    state = kit.state()
    assert state is not None and state.in_flight is None and state.hint_level == 2
    assert kit.row(rid).status == "delivered"


def test_finalize_db_failure_is_unavailable(kit: Kit) -> None:
    calls = _flaky_tx(kit, {2, 3})  # the finalization and its one retry are both busy
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert calls["n"] == 3
    assert out.status is HelpStatus.UNAVAILABLE
    assert out.html == render_help_html(messages.UNAVAILABLE)
    assert kit.usage()[0].state == "settled"  # settled before finalization
    state = kit.state()
    assert state is not None and state.in_flight == str(rid) and state.hint_level == 1
    assert kit.row(rid).output_json is None
