"""Help requests racing each other, submissions and "clear history" on a real SQLite file."""

from __future__ import annotations

import queue
import threading
import uuid
from pathlib import Path

from support.helpkit import WRONG_ANSWER, Kit, make_kit, output

from mathtutor.help.generator import GenerationRequest
from mathtutor.help.service import HelpOutcome, HelpStatus
from mathtutor.store.db import write_transaction
from mathtutor.store.models import User


def _run(kit: Kit, results: queue.Queue[object]) -> threading.Thread:
    def target() -> None:
        try:
            results.put(kit.help())
        except Exception as exc:  # noqa: BLE001 - the test inspects every outcome
            results.put(exc)

    thread = threading.Thread(target=target)
    thread.start()
    return thread


def test_concurrent_hints_advance_once(tmp_path: Path) -> None:
    """Both threads start together; whichever admits first blocks inside the provider call
    until the other has returned, so the second must see the item's help in flight."""
    kit = make_kit(tmp_path, [output(), output()])
    kit.submit_wrong()  # so the delivered hint moves the ladder (R35)
    release = threading.Event()
    kit.generator.before = lambda _req: release.wait(10)
    results: queue.Queue[object] = queue.Queue()
    barrier = threading.Barrier(2)

    def go() -> None:
        barrier.wait()
        try:
            results.put(kit.help())
        except Exception as exc:  # noqa: BLE001
            results.put(exc)

    threads = [threading.Thread(target=go) for _ in range(2)]
    for t in threads:
        t.start()
    first = results.get(timeout=10)
    release.set()
    second = results.get(timeout=10)
    for t in threads:
        t.join(10)
    assert isinstance(first, HelpOutcome) and isinstance(second, HelpOutcome)
    assert first.status is HelpStatus.PENDING
    assert second.status is HelpStatus.DELIVERED
    assert first.request_id == second.request_id  # pending names the in-flight request
    assert len(kit.generator.requests) == 1
    state = kit.state()
    assert state is not None and (state.hint_level, state.help_seq, state.in_flight) == (2, 1, None)
    assert len(kit.rows()) == 1 and len(kit.usage()) == 1


def test_submit_during_help_is_stale(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()])

    def submit(_req: GenerationRequest) -> None:
        kit.practice.submit_answer(
            kit.user,
            kit.session_id,
            uuid.uuid4(),
            kit.item.session_item_id,
            kit.item.revision,
            WRONG_ANSWER,
        )

    kit.generator.before = submit
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.STALE and out.html is None and out.sources == []
    row = kit.row(rid)
    assert row.status == "stale" and row.output_json is None
    (entry,) = kit.usage()
    assert entry.state == "settled" and (entry.input_tokens, entry.output_tokens) == (2000, 300)
    state = kit.state()
    assert state is not None and (state.hint_level, state.help_seq, state.in_flight) == (1, 0, None)
    item = kit.db_item()
    assert item.revision == 1 and item.tries_used == 1  # only the submission changed them


def test_clear_history_during_help_stores_nothing(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()])

    def clear(_req: GenerationRequest) -> None:
        with write_transaction(kit.sessions) as db:
            user = db.get(User, kit.user)
            assert user is not None
            user.privacy_epoch += 1

    kit.generator.before = clear
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.STALE and out.html is None
    row = kit.row(rid)
    assert row.output_json is None and row.status == "stale"
    assert kit.usage()[0].state == "settled"
    state = kit.state()
    assert state is not None and (state.hint_level, state.in_flight) == (1, None)
    # A retry of the same id never resurrects the text either.
    assert kit.help(rid=rid).status is HelpStatus.STALE


def test_many_concurrent_requests_one_in_flight(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output() for _ in range(6)])
    kit.submit_wrong()  # so the delivered hint moves the ladder (R35)
    release = threading.Event()
    kit.generator.before = lambda _req: release.wait(10)
    results: queue.Queue[object] = queue.Queue()
    threads = [_run(kit, results) for _ in range(6)]
    got = [results.get(timeout=15) for _ in range(5)]
    release.set()
    got.append(results.get(timeout=15))
    for t in threads:
        t.join(10)
    statuses = sorted(o.status for o in got if isinstance(o, HelpOutcome))
    assert len(statuses) == 6, got
    assert statuses.count(HelpStatus.DELIVERED) == 1
    assert set(statuses) <= {HelpStatus.DELIVERED, HelpStatus.PENDING, HelpStatus.UNAVAILABLE}
    assert len(kit.generator.requests) == 1
    assert kit.state().hint_level == 2  # type: ignore[union-attr]
