"""Durable admission and spend ledger (Task 8): fake clock, real SQLite file with WAL."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import AppError, HelpLimited
from mathtutor.domain import ItemState
from mathtutor.help.config import DEFAULT_CONFIG_PATH, load_help_config
from mathtutor.help.ledger import Ledger, main, micros_for
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade, write_transaction
from mathtutor.store.models import HelpRequestRow, SessionItem, StudySession, UsageEntry, User

CFG = load_help_config(DEFAULT_CONFIG_PATH)
HAIKU = "claude-haiku-5-5"
WORST = 1_300  # 8,000 × 0.1 + 1,000 × 0.5 µ$ (01-pinned-values)
START = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'ledger.db').as_posix()}"


@pytest.fixture
def engine(db_url: str) -> Iterator[Engine]:
    upgrade(db_url)
    eng = make_engine(db_url)
    yield eng
    eng.dispose()


@pytest.fixture
def sessions(engine: Engine) -> sessionmaker[Session]:
    return make_sessionmaker(engine)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(START)


@pytest.fixture
def ledger(sessions: sessionmaker[Session], clock: FakeClock) -> Ledger:
    return Ledger(sessions, CFG, clock)


def _rid() -> str:
    return str(uuid.uuid4())


def _admit(ledger: Ledger, sessions: sessionmaker[Session], user_id: int = 1) -> int:
    with write_transaction(sessions) as db:
        return ledger.admit(db, user_id, _rid(), HAIKU)


def _reason(ledger: Ledger, sessions: sessionmaker[Session], user_id: int = 1) -> str:
    with pytest.raises(HelpLimited) as info:
        _admit(ledger, sessions, user_id)
    return info.value.reason


def _seed_help_rows(sessions: sessionmaker[Session], n: int) -> int:
    """A real user with ``n`` help rows; returns the user id."""
    with write_transaction(sessions) as db:
        user = User(username=f"u{_rid()[:8]}", password_hash="x", created_at=START)
        sess = StudySession(user=user, mode="practice", topics=[], started_at=START)
        item = SessionItem(
            session=sess,
            item_id="i",
            content_version="v",
            problem_json="{}",
            sequence=1,
            state=ItemState.ACTIVE,
            revision=0,
            served_at=START,
            tries_used=0,
        )
        db.add_all([user, sess, item])
        db.flush()
        for k in range(n):
            db.add(
                HelpRequestRow(
                    request_id=_rid(),
                    user_id=user.id,
                    session_item_id=item.id,
                    item_revision=0,
                    help_type="hint",
                    payload_hash="h" * 64,
                    privacy_epoch=0,
                    help_seq=k + 1,
                    status="delivered",
                    prompt_version="v1",
                    corpus_hash="c",
                    index_fingerprint="f",
                    retrieved_ids=[],
                    cited_ids=[],
                    guard_counts={},
                    calls=1,
                    created_at=START,
                )
            )
        return user.id


def _clear_history_stub(sessions: sessionmaker[Session], user_id: int) -> None:
    """Task 12's clear-history path: delete help rows, bump the privacy epoch."""
    with write_transaction(sessions) as db:
        db.execute(delete(HelpRequestRow).where(HelpRequestRow.user_id == user_id))
        db.execute(
            update(User).where(User.id == user_id).values(privacy_epoch=User.privacy_epoch + 1)
        )


def _settle_month(sessions: sessionmaker[Session], micros: int, month: str = "2026-10") -> None:
    with write_transaction(sessions) as db:
        db.add(
            UsageEntry(
                request_id=_rid(),
                user_id=999,
                kind="help",
                call_no=1,
                model=HAIKU,
                month=month,
                state="settled",
                reserved_micros=micros,
                settled_micros=micros,
                created_at=START - timedelta(days=2),
                settled_at=START - timedelta(days=2),
            )
        )


def test_help_limited_error_shape() -> None:
    err = HelpLimited("hour")
    assert isinstance(err, AppError)
    assert (err.status, err.code, err.reason) == (429, "help_limited", "hour")


def test_worst_case_reservation(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    entry_id = _admit(ledger, sessions)
    with sessions() as db:
        row = db.get(UsageEntry, entry_id)
        assert row is not None
        assert (row.state, row.reserved_micros, row.call_no, row.month, row.kind) == (
            "reserved",
            WORST,
            1,
            "2026-10",
            "help",
        )
    assert ledger.month_total("2026-10") == WORST


def test_hourly_and_daily_limits(
    ledger: Ledger, sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    user_id = _seed_help_rows(sessions, 3)
    for _ in range(30):
        _admit(ledger, sessions, user_id)
        clock.advance(seconds=1)
    assert _reason(ledger, sessions, user_id) == "hour"
    # Deleting the user's help rows does not reset the count: it comes from the ledger.
    _clear_history_stub(sessions, user_id)
    assert _reason(ledger, sessions, user_id) == "hour"
    # Another student is unaffected.
    _admit(ledger, sessions, user_id + 1000)
    # Four more full hours: 150 within the trailing day.
    for _ in range(4):
        clock.advance(hours=1)
        for _ in range(30):
            _admit(ledger, sessions, user_id)
    clock.advance(hours=1, seconds=1)
    assert _reason(ledger, sessions, user_id) == "day"
    _clear_history_stub(sessions, user_id)
    assert _reason(ledger, sessions, user_id) == "day"
    # A day after the first batch, the window has rolled past it.
    clock.now = START + timedelta(days=1, minutes=1)
    _admit(ledger, sessions, user_id)


def test_later_calls_do_not_count_toward_rate(
    ledger: Ledger, sessions: sessionmaker[Session]
) -> None:
    for _ in range(29):
        _admit(ledger, sessions)
    rid = _rid()
    with write_transaction(sessions) as db:
        ledger.admit(db, 1, rid, HAIKU)
    ledger.reserve_call(rid, 1, 2, HAIKU)  # repair call: budget only, no rate count
    assert _reason(ledger, sessions) == "hour"


def test_budget_includes_reservations(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    _settle_month(sessions, 14_999_000)
    assert _reason(ledger, sessions) == "budget"
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(UsageEntry)) == 1


def test_budget_counts_open_reservations(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    _settle_month(sessions, 15_000_000 - 2 * WORST)
    _admit(ledger, sessions, 1)
    _admit(ledger, sessions, 2)  # exactly at the budget: allowed (≤)
    assert _reason(ledger, sessions, 3) == "budget"


def test_reserve_call_checks_budget(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    _settle_month(sessions, 15_000_000 - WORST)
    rid = _rid()
    with write_transaction(sessions) as db:
        ledger.admit(db, 1, rid, HAIKU)
    with pytest.raises(HelpLimited) as info:
        ledger.reserve_call(rid, 1, 2, HAIKU)
    assert info.value.reason == "budget"


def test_concurrent_admissions_do_not_overspend(
    sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    cfg = CFG.model_copy(
        update={"admission": CFG.admission.model_copy(update={"month_budget_micros": 10 * WORST})}
    )
    ledger = Ledger(sessions, cfg, clock)
    n = 20
    barrier = threading.Barrier(n)
    results: list[object] = [None] * n

    def run(i: int) -> None:
        barrier.wait()
        try:
            with write_transaction(sessions) as db:
                results[i] = ledger.admit(db, i + 1, _rid(), HAIKU)
        except Exception as exc:  # noqa: BLE001 - the test inspects every outcome
            results[i] = exc

    threads = [threading.Thread(target=run, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    ok = [r for r in results if isinstance(r, int)]
    limited = [r for r in results if isinstance(r, HelpLimited) and r.reason == "budget"]
    assert (len(ok), len(limited)) == (10, 10), results
    assert ledger.month_total("2026-10") == 10 * WORST


def test_settle_rounds_up(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    assert micros_for(CFG, HAIKU, 1_234, 567) == 407  # 406.9 µ$ → 407
    assert micros_for(CFG, HAIKU, 10, 0) == 1  # 0.001 µ$ → 1
    assert micros_for(CFG, HAIKU, 0, 0) == 0
    entry_id = _admit(ledger, sessions)
    assert ledger.settle(entry_id, 1_234, 567) == 407
    with sessions() as db:
        row = db.get(UsageEntry, entry_id)
        assert row is not None
        assert (row.state, row.settled_micros, row.input_tokens, row.output_tokens) == (
            "settled",
            407,
            1_234,
            567,
        )
        assert row.settled_at == START
    assert ledger.month_total("2026-10") == 407
    with pytest.raises(ValueError):
        ledger.settle(entry_id, 1, 1)


def test_uncertain_counts_until_reconciled(
    ledger: Ledger, sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    entry_id = _admit(ledger, sessions)
    clock.advance(seconds=120)
    assert ledger.reconcile_stale(clock()) == 0  # not older than 120 s yet
    clock.advance(seconds=1)
    assert ledger.reconcile_stale(clock()) == 1
    with sessions() as db:
        row = db.get(UsageEntry, entry_id)
        assert row is not None and row.state == "uncertain"
    assert ledger.month_total("2026-10") == WORST
    # A late settle with real token counts still resolves it.
    assert ledger.settle(entry_id, 1_234, 567) == 407
    assert ledger.month_total("2026-10") == 407


def test_admit_reconciles_first(
    ledger: Ledger, sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    first = _admit(ledger, sessions, 1)
    clock.advance(seconds=121)
    _admit(ledger, sessions, 2)
    with sessions() as db:
        row = db.get(UsageEntry, first)
        assert row is not None and row.state == "uncertain"


def test_mark_uncertain(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    entry_id = _admit(ledger, sessions)
    ledger.mark_uncertain(entry_id)
    with sessions() as db:
        row = db.get(UsageEntry, entry_id)
        assert row is not None and row.state == "uncertain"
    assert ledger.month_total("2026-10") == WORST


def test_month_rollover_utc(
    ledger: Ledger, sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    clock.now = datetime(2026, 10, 31, 23, 59, 59, tzinfo=UTC)
    settled = _admit(ledger, sessions, 1)
    ledger.settle(settled, 1_234, 567)
    stale = _admit(ledger, sessions, 2)
    with sessions() as db:
        assert {r.month for r in db.scalars(select(UsageEntry))} == {"2026-10"}
    clock.advance(seconds=1)
    assert ledger.month_total("2026-11") == 0
    clock.advance(minutes=5)
    _admit(ledger, sessions, 3)  # reconciles the old reservation to uncertain
    with sessions() as db:
        row = db.get(UsageEntry, stale)
        assert row is not None and (row.state, row.month) == ("uncertain", "2026-10")
    assert ledger.month_total("2026-10") == 407 + WORST
    assert ledger.month_total("2026-11") == WORST


def test_month_uses_utc_not_local_offset(
    ledger: Ledger, sessions: sessionmaker[Session], clock: FakeClock
) -> None:
    # 2026-11-01 01:00 at UTC+05:00 is still October in UTC.
    clock.now = datetime(2026, 11, 1, 1, 0, tzinfo=timezone(timedelta(hours=5)))
    entry_id = _admit(ledger, sessions)
    with sessions() as db:
        row = db.get(UsageEntry, entry_id)
        assert row is not None and row.month == "2026-10"


def test_clear_history_does_not_reset(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    user_id = _seed_help_rows(sessions, 2)
    for _ in range(5):
        _admit(ledger, sessions, user_id)
    total = ledger.month_total("2026-10")
    count = ledger.recent_admissions(user_id, timedelta(hours=1))
    _clear_history_stub(sessions, user_id)
    assert ledger.month_total("2026-10") == total == 5 * WORST
    assert ledger.recent_admissions(user_id, timedelta(hours=1)) == count == 5


def test_settle_uncertain_cli(
    ledger: Ledger,
    sessions: sessionmaker[Session],
    clock: FakeClock,
    db_url: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    a = _admit(ledger, sessions, 1)
    b = _admit(ledger, sessions, 2)
    ledger.mark_uncertain(a)
    ledger.mark_uncertain(b)
    assert main(["settle-uncertain", "--month", "2026-10", "--database-url", db_url]) == 0
    out = capsys.readouterr().out
    # Counts and totals only: no request ids, user ids or other student data.
    assert out.splitlines() == [
        f"2026-10: settled 2 uncertain entries for {2 * WORST} micro-USD",
        f"2026-10: month total {2 * WORST} micro-USD",
    ]
    with sessions() as db:
        states = {r.state for r in db.scalars(select(UsageEntry))}
    assert states == {"settled"}
    assert ledger.month_total("2026-10") == 2 * WORST


def test_settle_uncertain_cli_with_micros(
    ledger: Ledger,
    sessions: sessionmaker[Session],
    db_url: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    a = _admit(ledger, sessions, 1)
    keep = _admit(ledger, sessions, 2)  # still reserved: untouched
    ledger.mark_uncertain(a)
    assert (
        main(
            ["settle-uncertain", "--month", "2026-10", "--micros", "500", "--database-url", db_url]
        )
        == 0
    )
    capsys.readouterr()
    assert ledger.month_total("2026-10") == 500 + WORST
    with sessions() as db:
        row = db.get(UsageEntry, keep)
        assert row is not None and row.state == "reserved"


def test_settle_uncertain_cli_rejects_bad_month(db_url: str) -> None:
    with pytest.raises(SystemExit):
        main(["settle-uncertain", "--month", "2026-13", "--database-url", db_url])


def test_unknown_model_rejected(ledger: Ledger, sessions: sessionmaker[Session]) -> None:
    with pytest.raises(ValueError), write_transaction(sessions) as db:
        ledger.admit(db, 1, _rid(), "no-such-model")
