"""Durable admission and spend ledger for Claude-written help.

Every provider call has a ``UsageEntry``: reserved at its worst case before the call, settled at
its actual cost after it. Money is integer micro-USD; months are UTC ``YYYY-MM``.

``admit`` runs inside the caller's ``write_transaction`` (``BEGIN IMMEDIATE``), so admissions are
serialized by SQLite's write lock: two requests cannot both see room for one more reservation.
Callers commit before calling the provider, so no lock is held during a call. Rate limits count
the ledger's ``call_no == 1`` entries, not help rows, so clearing history never resets them.

A reservation not settled within ``uncertain_after_s`` becomes ``uncertain`` and keeps counting
at its worst case. Nothing settles ``uncertain`` automatically; after checking the provider
console the owner runs::

    python -m mathtutor.help.ledger settle-uncertain --month YYYY-MM [--micros N]
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import HelpLimited
from mathtutor.help.config import (
    DEFAULT_CONFIG_PATH,
    HelpConfig,
    load_help_config,
    worst_case_micros,
)
from mathtutor.store.db import make_engine, make_sessionmaker, write_transaction
from mathtutor.store.models import UsageEntry

RESERVED, SETTLED, UNCERTAIN = "reserved", "settled", "uncertain"
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
HOUR, DAY = timedelta(hours=1), timedelta(days=1)


def micros_for(cfg: HelpConfig, model: str, input_tokens: int, output_tokens: int) -> int:
    """Actual cost of one call in micro-USD, rounded up (integer arithmetic only)."""
    tariff = cfg.tariffs.get(model)
    if tariff is None:
        raise ValueError(f"no tariff for model {model!r}")
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    numerator = (
        input_tokens * tariff.input_micros_per_mtok + output_tokens * tariff.output_micros_per_mtok
    )
    return -(-numerator // 1_000_000)


def month_of(when: datetime) -> str:
    """UTC calendar month ``YYYY-MM`` of an aware timestamp."""
    if when.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return when.astimezone(UTC).strftime("%Y-%m")


def _month_total(db: Session, month: str) -> int:
    amount = case(
        (UsageEntry.state == SETTLED, UsageEntry.settled_micros), else_=UsageEntry.reserved_micros
    )
    total = db.scalar(select(func.coalesce(func.sum(amount), 0)).where(UsageEntry.month == month))
    return int(total or 0)


class Ledger:
    def __init__(
        self, sessions: sessionmaker[Session], cfg: HelpConfig, clock: Callable[[], datetime]
    ) -> None:
        self._sessions = sessions
        self._cfg = cfg
        self._clock = clock

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("clock must return timezone-aware datetimes")
        return now.astimezone(UTC)

    # -- admission ---------------------------------------------------------------------------

    def admit(
        self, db: Session, user_id: int, request_id: str, model: str, *, kind: str = "help"
    ) -> int:
        """Admit a logical request inside the caller's write transaction; reserve call 1.

        Raises ``HelpLimited("hour" | "day" | "budget")``. Returns the usage entry id.
        """
        now = self._now()
        self._reconcile(db, now)
        limits = self._cfg.admission
        if self._count_admissions(db, user_id, now - HOUR) >= limits.per_hour:
            raise HelpLimited("hour")
        if self._count_admissions(db, user_id, now - DAY) >= limits.per_day:
            raise HelpLimited("day")
        return self._reserve(db, now, request_id, user_id, 1, model, kind)

    def reserve_call(
        self, request_id: str, user_id: int, call_no: int, model: str, *, kind: str = "help"
    ) -> int:
        """Reserve a later call of an admitted request: budget check only, own transaction."""
        with write_transaction(self._sessions) as db:
            now = self._now()
            self._reconcile(db, now)
            return self._reserve(db, now, request_id, user_id, call_no, model, kind)

    def _reserve(
        self,
        db: Session,
        now: datetime,
        request_id: str,
        user_id: int,
        call_no: int,
        model: str,
        kind: str,
    ) -> int:
        worst = worst_case_micros(self._cfg, model)
        month = month_of(now)
        if _month_total(db, month) + worst > self._cfg.admission.month_budget_micros:
            raise HelpLimited("budget")
        entry = UsageEntry(
            request_id=request_id,
            user_id=user_id,
            kind=kind,
            call_no=call_no,
            model=model,
            month=month,
            state=RESERVED,
            reserved_micros=worst,
            settled_micros=None,
            input_tokens=0,
            output_tokens=0,
            created_at=now,
            settled_at=None,
        )
        db.add(entry)
        db.flush()
        return entry.id

    @staticmethod
    def _count_admissions(db: Session, user_id: int, since: datetime) -> int:
        count = db.scalar(
            select(func.count())
            .select_from(UsageEntry)
            .where(
                UsageEntry.user_id == user_id,
                UsageEntry.kind == "help",
                UsageEntry.call_no == 1,
                UsageEntry.created_at > since,
            )
        )
        return int(count or 0)

    def recent_admissions(self, user_id: int, window: timedelta) -> int:
        """Admitted help requests by ``user_id`` within the trailing ``window``."""
        with self._sessions() as db:
            return self._count_admissions(db, user_id, self._now() - window)

    # -- settlement --------------------------------------------------------------------------

    def settle(self, entry_id: int, input_tokens: int, output_tokens: int) -> int:
        """Record a call's actual cost (rounded up); also resolves an ``uncertain`` entry."""
        with write_transaction(self._sessions) as db:
            entry = db.get(UsageEntry, entry_id)
            if entry is None:
                raise ValueError(f"no usage entry {entry_id}")
            if entry.state == SETTLED:
                raise ValueError(f"usage entry {entry_id} is already settled")
            micros = micros_for(self._cfg, entry.model, input_tokens, output_tokens)
            entry.state = SETTLED
            entry.settled_micros = micros
            entry.input_tokens = input_tokens
            entry.output_tokens = output_tokens
            entry.settled_at = self._now()
            return micros

    def mark_uncertain(self, entry_id: int) -> None:
        """The provider may have billed but reported no usage: keep the worst case counting."""
        with write_transaction(self._sessions) as db:
            db.execute(
                update(UsageEntry)
                .where(UsageEntry.id == entry_id, UsageEntry.state == RESERVED)
                .values(state=UNCERTAIN)
            )

    def reconcile_stale(self, now: datetime) -> int:
        """Mark reservations older than ``uncertain_after_s`` as uncertain; returns how many."""
        with write_transaction(self._sessions) as db:
            return self._reconcile(db, now)

    def _reconcile(self, db: Session, now: datetime) -> int:
        cutoff = now.astimezone(UTC) - timedelta(seconds=self._cfg.admission.uncertain_after_s)
        result = db.execute(
            update(UsageEntry)
            .where(UsageEntry.state == RESERVED, UsageEntry.created_at < cutoff)
            .values(state=UNCERTAIN)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    def month_total(self, month: str) -> int:
        """Settled amounts plus reserved and uncertain worst cases for a UTC month."""
        with self._sessions() as db:
            return _month_total(db, month)

    def settle_uncertain(self, month: str, micros: int | None = None) -> tuple[int, int]:
        """Settle every ``uncertain`` entry of ``month`` at its reserved worst case, or at
        ``micros`` each. Returns (entries settled, micro-USD settled)."""
        if not MONTH_RE.match(month):
            raise ValueError(f"month must be YYYY-MM, got {month!r}")
        if micros is not None and micros < 0:
            raise ValueError("micros must be non-negative")
        with write_transaction(self._sessions) as db:
            rows = db.scalars(
                select(UsageEntry).where(UsageEntry.month == month, UsageEntry.state == UNCERTAIN)
            ).all()
            now = self._now()
            total = 0
            for row in rows:
                row.state = SETTLED
                row.settled_micros = row.reserved_micros if micros is None else micros
                row.settled_at = now
                total += row.settled_micros
            return len(rows), total


def _month_arg(value: str) -> str:
    if not MONTH_RE.match(value):
        raise argparse.ArgumentTypeError("month must be YYYY-MM")
    return value


def _micros_arg(value: str) -> int:
    n = int(value)
    if n < 0:
        raise argparse.ArgumentTypeError("micros must be non-negative")
    return n


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathtutor.help.ledger")
    sub = parser.add_subparsers(dest="command", required=True)
    settle = sub.add_parser("settle-uncertain", help="settle uncertain reservations by hand")
    settle.add_argument("--month", type=_month_arg, required=True, help="UTC month YYYY-MM")
    settle.add_argument(
        "--micros", type=_micros_arg, help="micro-USD per entry (default: reserved worst case)"
    )
    settle.add_argument("--database-url", help="default: MATHTUTOR_DATABASE_URL")
    args = parser.parse_args(argv)

    if args.database_url is None:
        from mathtutor.settings import Settings

        settings = Settings()
        url, cfg_path = settings.database_url, settings.help_config_path
    else:
        url, cfg_path = args.database_url, DEFAULT_CONFIG_PATH
    engine = make_engine(url)
    try:
        ledger = Ledger(
            make_sessionmaker(engine), load_help_config(cfg_path), lambda: datetime.now(UTC)
        )
        count, settled = ledger.settle_uncertain(args.month, args.micros)
        total = ledger.month_total(args.month)
    finally:
        engine.dispose()
    # Counts and totals only: never request ids, user ids or any student data.
    print(f"{args.month}: settled {count} uncertain entries for {settled} micro-USD")
    print(f"{args.month}: month total {total} micro-USD")
    return 0


if __name__ == "__main__":
    sys.exit(main())
