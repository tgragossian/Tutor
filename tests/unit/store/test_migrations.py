import sqlite3

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text

from mathtutor.store.db import downgrade, make_engine, upgrade
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


def test_transactions_begin_immediate(db_url: str) -> None:
    """A transaction takes the write lock when it begins, so writers queue on busy_timeout
    instead of failing when a read lock cannot be upgraded."""
    upgrade(db_url)
    engine = make_engine(db_url)
    path = db_url.removeprefix("sqlite:///")
    try:
        with engine.connect() as conn, conn.begin():
            conn.execute(text("SELECT 1"))
            other = sqlite3.connect(path, timeout=0)
            try:
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    other.execute("BEGIN IMMEDIATE")
            finally:
                other.close()
    finally:
        engine.dispose()
