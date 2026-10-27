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


def _populate_0004(path: str) -> None:
    raw = sqlite3.connect(path)
    raw.executescript(
        """
        INSERT INTO users (id, username, password_hash, created_at)
            VALUES (1, 'ann', 'x', '2026-10-01 00:00:00');
        INSERT INTO study_sessions (id, user_id, mode, topics, started_at)
            VALUES (1, 1, 'practice', '[]', '2026-10-01 00:00:00');
        INSERT INTO session_items (id, session_id, item_id, content_version, problem_json,
            sequence, state, revision, served_at, tries_used)
            VALUES (1, 1, 'i', 'v', '{}', 1, 'active', 0, '2026-10-01 00:00:00', 0);
        INSERT INTO help_requests (request_id, user_id, session_item_id, item_revision,
            help_type, payload_hash, privacy_epoch, help_seq, status, prompt_version,
            corpus_hash, index_fingerprint, retrieved_ids, cited_ids, guard_counts, calls,
            created_at)
            VALUES ('r1', 1, 1, 0, 'hint', 'h', 0, 1, 'ok', 'p', 'c', 'f', '[]', '[]', '{}', 1,
            '2026-10-01 00:00:00');
        INSERT INTO usage_entries (request_id, user_id, kind, call_no, model, month, state,
            reserved_micros, created_at)
            VALUES ('r1', 1, 'help', 1, 'm', '2026-10', 'reserved', 5,
            '2026-10-01 00:00:00');
        """
    )
    raw.commit()
    raw.close()


def test_downgrade_0004(db_url: str) -> None:
    upgrade(db_url)
    path = db_url.removeprefix("sqlite:///")
    _populate_0004(path)
    downgrade(db_url, "0003")
    tables = _tables(db_url)
    assert not {"help_requests", "item_help_state", "usage_entries"} & tables
    engine = make_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("users")}
        assert "privacy_epoch" not in cols
        with engine.connect() as conn:
            assert conn.execute(text("SELECT id, username FROM users")).all() == [(1, "ann")]
            assert conn.execute(text("SELECT user_id FROM study_sessions")).all() == [(1,)]
            assert conn.execute(text("SELECT session_id FROM session_items")).all() == [(1,)]
            assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        engine.dispose()
    upgrade(db_url)
    assert "usage_entries" in _tables(db_url)


def test_server_defaults_apply_to_raw_inserts(db_url: str) -> None:
    upgrade(db_url)
    path = db_url.removeprefix("sqlite:///")
    _populate_0004(path)
    raw = sqlite3.connect(path)
    raw.execute("INSERT INTO item_help_state (session_item_id) VALUES (1)")
    raw.execute(
        "INSERT INTO help_requests (request_id, user_id, session_item_id, item_revision,"
        " help_type, payload_hash, privacy_epoch, help_seq, status, prompt_version,"
        " corpus_hash, index_fingerprint, retrieved_ids, cited_ids, guard_counts, calls,"
        " created_at) VALUES ('r2', 1, 1, 0, 'hint', 'h', 0, 1, 'ok', 'p', 'c', 'f',"
        " '[]', '[]', '{}', 1, '2026-10-01 00:00:00')"
    )
    raw.commit()
    state = raw.execute("SELECT hint_level, help_seq FROM item_help_state").fetchone()
    arm = raw.execute("SELECT arm FROM help_requests WHERE request_id='r2'").fetchone()
    raw.close()
    assert state == (1, 0)
    assert arm == ("none",)


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
