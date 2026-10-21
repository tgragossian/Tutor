"""Overlapping submissions through the real verifier pool and a real SQLite file."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import func, select
from support import checks

from mathtutor.application.auth import AuthService
from mathtutor.application.errors import Busy, StaleItem
from mathtutor.application.practice import ItemView, PracticeService, SubmitView
from mathtutor.content.loader import load_bundle
from mathtutor.domain import AnswerKind, ItemState
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade
from mathtutor.store.models import AttemptResult
from mathtutor.verify.pool import VerifierPool
from mathtutor.verify.types import SubmittedAnswer

ROOT = Path(__file__).resolve().parents[2]
CONTENT = load_bundle(ROOT / "content" / "compiled" / "problems.json")
ANSWER = SubmittedAnswer(AnswerKind.EXPRESSION, ["Multiply", 2, "x"], "2x", None)


def _now() -> datetime:
    return datetime.now(UTC)


@pytest.fixture
def setup(tmp_path: Path) -> Iterator[tuple[PracticeService, AuthService, VerifierPool, object]]:
    url = f"sqlite:///{(tmp_path / 'race.db').as_posix()}"
    upgrade(url)
    engine = make_engine(url)
    sessions = make_sessionmaker(engine)
    pool = VerifierPool(size=1, memory_mb=None, check_fn=checks.slow)
    try:
        yield (
            PracticeService(sessions, CONTENT, pool, _now),
            AuthService(sessions, _now),
            pool,
            sessions,
        )
    finally:
        pool.close()
        engine.dispose()


def _run_threads(fns: list[Callable[[], object]]) -> list[object]:
    results: list[object] = [None] * len(fns)
    barrier = threading.Barrier(len(fns))

    def run(i: int) -> None:
        barrier.wait()
        try:
            results[i] = fns[i]()
        except Exception as exc:  # noqa: BLE001 - the test inspects every outcome
            results[i] = exc

    threads = [threading.Thread(target=run, args=(i,)) for i in range(len(fns))]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def test_racing_different_submission_ids_one_wins(setup) -> None:  # type: ignore[no-untyped-def]
    svc, auth, pool, sessions = setup
    pool._check_fn_for_test(checks.slow)
    user = auth.register("racer", "password-1").user_id
    sid = svc.start_session(user, ["derivatives.basic_rules"])
    v = svc.current_item(user, sid)
    assert isinstance(v, ItemView)

    def submit() -> SubmitView:
        return svc.submit_answer(user, sid, uuid.uuid4(), v.session_item_id, v.revision, ANSWER)

    results = _run_threads([submit, submit])
    wins = [r for r in results if isinstance(r, SubmitView)]
    stale = [r for r in results if isinstance(r, StaleItem)]
    assert len(wins) == 1 and len(stale) == 1, results
    assert wins[0].item.state is ItemState.ANSWERED
    with sessions() as db:  # type: ignore[operator]
        applied = db.scalars(select(AttemptResult.applied)).all()
    assert sorted(applied) == [False, True]


def test_sixteen_concurrent_submits(setup) -> None:  # type: ignore[no-untyped-def]
    svc, auth, pool, sessions = setup
    pool._check_fn_for_test(checks.ok)
    targets = []
    for i in range(16):
        user = auth.register(f"user_{i:02d}", "password-1").user_id
        sid = svc.start_session(user, ["derivatives.basic_rules"])
        v = svc.current_item(user, sid)
        assert isinstance(v, ItemView)
        targets.append((user, sid, v))

    def make(user: int, sid: int, v: ItemView) -> Callable[[], SubmitView]:
        return lambda: svc.submit_answer(
            user, sid, uuid.uuid4(), v.session_item_id, v.revision, ANSWER
        )

    results = _run_threads([make(*t) for t in targets])
    kinds = {type(r).__name__ for r in results}
    assert kinds <= {"SubmitView", "StaleItem", "Busy"}, results
    assert any(isinstance(r, SubmitView) for r in results)
    with sessions() as db:  # type: ignore[operator]
        n = db.scalar(select(func.count()).select_from(AttemptResult))
    assert n == sum(isinstance(r, SubmitView) for r in results)
    assert not any(isinstance(r, Busy) and r.status != 503 for r in results)


def test_sixteen_racers_on_one_item(setup) -> None:  # type: ignore[no-untyped-def]
    svc, auth, pool, sessions = setup
    pool._check_fn_for_test(checks.slow)
    user = auth.register("crowd", "password-1").user_id
    sid = svc.start_session(user, ["derivatives.basic_rules"])
    v = svc.current_item(user, sid)
    assert isinstance(v, ItemView)

    def submit() -> SubmitView:
        return svc.submit_answer(user, sid, uuid.uuid4(), v.session_item_id, v.revision, ANSWER)

    results = _run_threads([submit] * 16)
    kinds = sorted(type(r).__name__ for r in results)
    assert kinds.count("SubmitView") == 1, kinds
    assert set(kinds) <= {"SubmitView", "StaleItem", "Busy"}, results
    assert "Busy" in kinds  # pool size 1, queue 8, 1 s checks: the queue overflows
    with sessions() as db:  # type: ignore[operator]
        applied = db.scalars(select(AttemptResult.applied)).all()
    assert sorted(applied).count(True) == 1
    # Busy releases its reservation; a stale racer stored at most one unapplied result.
    assert len(applied) <= kinds.count("SubmitView") + kinds.count("StaleItem")
