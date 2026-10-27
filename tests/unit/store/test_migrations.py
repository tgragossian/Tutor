import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from mathtutor.store.db import (
    downgrade,
    make_engine,
    make_sessionmaker,
    upgrade,
    write_transaction,
)
from mathtutor.store.models import Base

TABLES = {
    "users",
    "web_sessions",
    "study_sessions",
    "session_items",
    "submissions",
    "attempt_results",
    "item_events",
    "alembic_version",
}


def _tables(url: str) -> set[str]:
    engine = make_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_creates_all_tables(db_url: str) -> None:
    url = db_url
    upgrade(url)
    assert _tables(url) >= TABLES


def test_migration_matches_models(db_url: str) -> None:
    url = db_url
    upgrade(url)
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn, opts={"compare_type": True})
            diff = compare_metadata(ctx, Base.metadata)
    finally:
        engine.dispose()
    assert diff == []


def test_pragmas(db_url: str) -> None:
    url = db_url
    upgrade(url)
    engine = make_engine(url)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA journal_mode")).scalar() == "wal"
            assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
            assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        engine.dispose()


def test_downgrade_then_upgrade(db_url: str) -> None:
    url = db_url
    upgrade(url)
    downgrade(url, "base")
    assert _tables(url) <= {"alembic_version"}
    upgrade(url)
    assert _tables(url) >= TABLES


def _write_lock_free(path: str) -> bool:
    other = sqlite3.connect(path, timeout=0)
    try:
        other.execute("BEGIN IMMEDIATE")
        other.rollback()
        return True
    except sqlite3.OperationalError as exc:
        assert "locked" in str(exc)
        return False
    finally:
        other.close()


def test_upgrade_0003_to_0004_keeps_rows(db_url: str) -> None:
    upgrade(db_url, "0003")
    path = db_url.removeprefix("sqlite:///")
    raw = sqlite3.connect(path)
    raw.execute(
        "INSERT INTO users (username, password_hash, created_at) "
        "VALUES ('ann', 'x', '2026-10-01 00:00:00')"
    )
    raw.commit()
    raw.close()
    upgrade(db_url)
    engine = make_engine(db_url)
    try:
        with engine.connect() as conn:
            row = conn.execute(text("SELECT username, privacy_epoch FROM users")).one()
        assert tuple(row) == ("ann", 0)
        assert {"help_requests", "item_help_state", "usage_entries"} <= set(
            inspect(engine).get_table_names()
        )
    finally:
        engine.dispose()


def test_downgrade_0004(db_url: str) -> None:
    upgrade(db_url)
    downgrade(db_url, "0003")
    tables = _tables(db_url)
    assert not {"help_requests", "item_help_state", "usage_entries"} & tables
    engine = make_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("users")}
    finally:
        engine.dispose()
    assert "privacy_epoch" not in cols
    upgrade(db_url)
    assert "usage_entries" in _tables(db_url)


def test_write_transactions_begin_immediate_reads_do_not(db_url: str) -> None:
    """A write transaction takes the write lock when it begins, so writers queue on
    busy_timeout instead of failing on a lock upgrade; reads take no lock (review B-A3)."""
    upgrade(db_url)
    engine = make_engine(db_url)
    sessions = make_sessionmaker(engine)
    path = db_url.removeprefix("sqlite:///")
    try:
        with write_transaction(sessions) as db:
            db.execute(text("SELECT 1"))
            assert not _write_lock_free(path)
        with sessions() as db:
            db.execute(text("SELECT 1"))
            assert _write_lock_free(path)
    finally:
        engine.dispose()
