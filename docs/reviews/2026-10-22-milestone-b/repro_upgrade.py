"""Check migration 0003 on populated 0002 data, including a result and an orphan."""

import json
import sqlite3

from support.content import core_content

from mathtutor.store.db import upgrade


def test_0003_preserves_populated_0002_rows_and_foreign_keys(tmp_path):
    path = tmp_path / "legacy.db"
    url = f"sqlite:///{path.as_posix()}"
    upgrade(url, "0002")
    content = core_content()
    problem = content.bundle.problems[0]
    at = "2026-10-22 12:00:00"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("INSERT INTO users VALUES (1, 'migrate', 'unused', ?)", (at,))
        db.execute(
            "INSERT INTO study_sessions (id,user_id,mode,topics,started_at) VALUES (1,1,?,?,?)",
            ("practice", json.dumps([problem.topic]), at),
        )
        db.execute(
            "INSERT INTO session_items (id,session_id,item_id,content_version,problem_json,"
            "sequence,state,revision,served_at,tries_used) VALUES (1,1,?,?,?,1,'active',1,?,1)",
            (problem.id, content.versions[problem.id], problem.model_dump_json(), at),
        )
        for pk in (1, 2):
            db.execute(
                "INSERT INTO submissions VALUES (?,?,1,'expression',?,?,?)",
                (pk, f"legacy-{pk}", '{"mathjson":1,"choice_id":null}', "1", at),
            )
        db.execute(
            "INSERT INTO attempt_results VALUES "
            "(1,1,'incorrect','counterexample','refutation','old',7,1,42,1,1)"
        )
        original = db.execute("SELECT * FROM submissions ORDER BY id").fetchall()
        result = db.execute("SELECT * FROM attempt_results").fetchall()
        root = db.execute("SELECT rootpage FROM sqlite_master WHERE name='submissions'").fetchone()
    upgrade(url, "0003")
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT * FROM submissions ORDER BY id").fetchall()
        assert [row[:7] for row in rows] == original
        assert [row[7:] for row in rows] == [(None, 0, None)] * 2
        assert db.execute("SELECT * FROM attempt_results").fetchall() == result
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("0003",)
        assert (
            db.execute("SELECT rootpage FROM sqlite_master WHERE name='submissions'").fetchone()
            == root
        )
