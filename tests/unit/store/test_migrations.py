import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text

from mathtutor.store.db import (
    downgrade,
    make_engine,
    make_sessionmaker,
    upgrade,
    write_transaction,
)
from mathtutor.store.models import Answer, Base

TABLES = {
    "users",
    "web_sessions",
    "study_sessions",
    "session_items",
    "answers",
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
    state = raw.execute("SELECT start_hints, help_seq FROM item_help_state").fetchone()
    arm = raw.execute("SELECT arm FROM help_requests WHERE request_id='r2'").fetchone()
    raw.close()
    assert state == (0, 0)
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


def test_0005_adds_hint_ladder_columns_and_downgrades(db_url: str) -> None:
    """R35: nullable columns only; 0004 rows survive the upgrade and the downgrade."""
    upgrade(db_url, "0005")
    path = db_url.removeprefix("sqlite:///")
    _populate_0004(path)
    raw = sqlite3.connect(path)
    raw.execute("INSERT INTO item_help_state (session_item_id) VALUES (1)")
    raw.commit()
    raw.close()
    engine = make_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("item_help_state")}
        assert {"hint_attempt_pk", "hint_type", "hint_counts", "start_hints"} <= cols
        cols = {c["name"] for c in inspect(engine).get_columns("help_requests")}
        assert {"mistake_type", "start_step"} <= cols
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT hint_level, hint_attempt_pk, hint_type, hint_counts"
                    " FROM item_help_state"
                )
            ).one()
        assert tuple(row) == (1, None, None, "{}")
    finally:
        engine.dispose()
    downgrade(db_url, "0004")
    engine = make_engine(db_url)
    try:
        cols = {c["name"] for c in inspect(engine).get_columns("item_help_state")}
        assert not {"hint_attempt_pk", "hint_type", "hint_counts", "start_hints"} & cols
        with engine.connect() as conn:
            assert conn.execute(text("SELECT request_id FROM help_requests")).all() == [("r1",)]
    finally:
        engine.dispose()


def _populate_0005(path: str) -> None:
    """Old rows on two items: applied incorrect (1, labeled by the last hint), applied correct
    (2), an unapplied result (3), an orphan with no result (4) and a pre-0003 orphan with a
    NULL reserved_revision (5). Item 2's hint state points at the correct answer."""
    _populate_0004(path)
    raw = sqlite3.connect(path)
    raw.executescript(
        """
        INSERT INTO session_items (id, session_id, item_id, content_version, problem_json,
            sequence, state, revision, served_at, tries_used)
            VALUES (2, 1, 'j', 'v', '{}', 2, 'active', 0, '2026-10-01 00:00:00', 0);
        INSERT INTO submissions (id, submission_id, session_item_id, answer_kind, answer_json,
            answer_latex, created_at, reserved_revision, lease, leased_at) VALUES
            (1, 's1', 1, 'expression', '{"mathjson": ["Multiply", 2, "x"], "choice_id": null}',
                '2x', '2026-10-01 00:01:00.000000', 0, 0, NULL),
            (2, 's2', 1, 'expression', '{"mathjson": ["Power", "x", 2], "choice_id": null}',
                'x^2', '2026-10-01 00:02:00.000000', 1, 1, '2026-10-01 00:02:30.000000'),
            (3, 's3', 1, 'choice', '{"mathjson": null, "choice_id": "b"}',
                NULL, '2026-10-01 00:03:00.000000', 1, 0, NULL),
            (4, 's4', 2, 'expression', '{"mathjson": 100000000000000000001, "choice_id": null}',
                '3', '2026-10-01 00:04:00.000000', 0, 0, NULL),
            (5, 's5', 2, 'expression',
                '{"mathjson": ["Multiply", {"num": "0.1"}, "x"], ' || '"choice_id": null}',
                '4', '2026-10-01 00:05:00.000000', NULL, 0, NULL);
        INSERT INTO attempt_results (id, submission_pk, status, reason, method,
            verifier_version, worker_ms, queue_ms, seconds_on_item, counts_as_try, applied)
            VALUES
            (7, 1, 'incorrect', 'counterexample', 'refutation', 'v1', 11, 1, 60, 1, 1),
            (8, 3, 'correct', 'proven', 'symbolic', 'v1', 13, 3, 180, 0, 0),
            (9, 2, 'correct', 'proven', 'symbolic', 'v1', 12, 2, 120, 0, 1);
        INSERT INTO item_help_state (session_item_id, hint_attempt_pk, hint_type)
            VALUES (1, 1, 'algebra'), (2, 2, 'wrong_rule');
        """
    )
    raw.commit()
    raw.close()


def _rows(path: str, sql: str) -> list[tuple[object, ...]]:
    raw = sqlite3.connect(path)
    try:
        return raw.execute(sql).fetchall()
    finally:
        raw.close()


BIG = "100000000000000000001"  # 10**20 + 1: past int64, so NUMERIC affinity would make it REAL
DECIMAL = '["Multiply", {"num": "0.1"}, "x"]'

_OLD_SUBMISSIONS = "SELECT * FROM submissions ORDER BY id"
_OLD_RESULTS = (
    "SELECT submission_pk, status, reason, method, verifier_version, worker_ms, queue_ms,"
    " seconds_on_item, counts_as_try, applied FROM attempt_results ORDER BY submission_pk"
)


def test_0006_copies_answers_with_attempt_numbers(db_url: str) -> None:
    upgrade(db_url, "0005")
    path = db_url.removeprefix("sqlite:///")
    _populate_0005(path)
    upgrade(db_url)
    assert not {"submissions", "attempt_results"} & _tables(db_url)
    rows = _rows(
        path,
        "SELECT id, submission_id, user_id, session_item_id, attempt_no, answer_kind,"
        " mathjson, choice_id, latex, created_at, reserved_revision, lease, leased_at,"
        " status, reason, method, verifier_version, worker_ms, queue_ms, seconds_on_item,"
        " counts_as_try, applied, mistake_type FROM answers ORDER BY id",
    )
    t = "2026-10-01 00:0{}:00.000000".format
    graded = ("v1",)
    assert rows == [
        (1, "s1", 1, 1, 1, "expression", '["Multiply", 2, "x"]', None, "2x", t(1), 0, 0, None)
        + ("incorrect", "counterexample", "refutation", *graded, 11, 1, 60, 1, 1, "algebra"),
        (2, "s2", 1, 1, 2, "expression", '["Power", "x", 2]', None, "x^2", t(2), 1, 1)
        + ("2026-10-01 00:02:30.000000", "correct", "proven", "symbolic", *graded)
        + (12, 2, 120, 0, 1, None),
        (3, "s3", 1, 1, None, "choice", None, "b", None, t(3), 1, 0, None)
        + ("correct", "proven", "symbolic", *graded, 13, 3, 180, 0, 0, None),
        (4, "s4", 1, 2, None, "expression", BIG, None, "3", t(4), 0, 0, None)
        + (None,) * 9
        + (None,),
        (5, "s5", 1, 2, None, "expression", DECIMAL, None, "4", t(5), None, 0, None)
        + (None,) * 9
        + (None,),
    ]
    engine = make_engine(db_url)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
        with make_sessionmaker(engine)() as db:
            copied = {a.id: a.mathjson for a in db.scalars(select(Answer))}
        assert copied[4] == 10**20 + 1  # read back exactly through the ORM
        assert copied[5] == ["Multiply", {"num": "0.1"}, "x"]
    finally:
        engine.dispose()


def test_0006_downgrade_round_trip(db_url: str) -> None:
    """Old rows come back unchanged; only ``attempt_results.id`` is renumbered."""
    upgrade(db_url, "0005")
    path = db_url.removeprefix("sqlite:///")
    _populate_0005(path)
    before = _rows(path, _OLD_SUBMISSIONS), _rows(path, _OLD_RESULTS)
    upgrade(db_url)
    downgrade(db_url, "0005")
    assert "answers" not in _tables(db_url)
    assert (_rows(path, _OLD_SUBMISSIONS), _rows(path, _OLD_RESULTS)) == before
    assert _rows(path, "SELECT id FROM attempt_results ORDER BY id") == [(1,), (2,), (3,)]
    upgrade(db_url)
    assert _rows(path, "SELECT attempt_no FROM answers ORDER BY id") == [
        (1,),
        (2,),
        (None,),
        (None,),
        (None,),
    ]


def _columns(url: str, table: str) -> set[str]:
    engine = make_engine(url)
    try:
        return {c["name"] for c in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


_COUNTERS = {"hint_attempt_pk", "hint_type", "hint_counts", "hint_level"}


def test_0007_round_trip(db_url: str) -> None:
    """Spec D9/D10: ``help_requests.answer_id`` (old rows NULL) and the R35 counters dropped;
    the downgrade re-adds the counters with their old defaults and keeps every row."""
    upgrade(db_url, "0005")
    path = db_url.removeprefix("sqlite:///")
    _populate_0005(path)
    upgrade(db_url, "0006")
    labels = _rows(path, "SELECT id, mistake_type FROM answers ORDER BY id")
    upgrade(db_url)
    assert not _COUNTERS & _columns(db_url, "item_help_state")
    assert _columns(db_url, "item_help_state") == {
        "session_item_id",
        "start_hints",
        "help_seq",
        "in_flight",
    }
    kept = "SELECT session_item_id, start_hints, help_seq, in_flight FROM item_help_state"
    assert _rows(path, kept + " ORDER BY session_item_id") == [
        (1, 0, 0, None),
        (2, 0, 0, None),
    ]
    assert _rows(path, "SELECT request_id, answer_id FROM help_requests") == [("r1", None)]
    assert _rows(path, "SELECT id, mistake_type FROM answers ORDER BY id") == labels
    raw = sqlite3.connect(path)
    raw.execute("PRAGMA foreign_keys=ON")
    raw.execute("UPDATE help_requests SET answer_id = 1")
    raw.commit()
    try:
        raw.execute("UPDATE help_requests SET answer_id = 99")  # no such answer
        raw.commit()
        raise AssertionError("answer_id must reference answers.id")
    except sqlite3.IntegrityError:
        raw.rollback()
    finally:
        raw.close()
    downgrade(db_url, "0006")
    assert "answer_id" not in _columns(db_url, "help_requests")
    assert _rows(
        path,
        "SELECT session_item_id, hint_level, hint_attempt_pk, hint_type, hint_counts,"
        " start_hints, help_seq FROM item_help_state ORDER BY session_item_id",
    ) == [(1, 1, None, None, "{}", 0, 0), (2, 1, None, None, "{}", 0, 0)]
    assert _rows(path, "SELECT request_id FROM help_requests") == [("r1",)]
    upgrade(db_url)
    assert "answer_id" in _columns(db_url, "help_requests")
