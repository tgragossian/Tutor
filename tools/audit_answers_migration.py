"""Compare a pre-0006 SQLite backup with its upgraded copy; exit nonzero on data loss.

Usage: python tools/audit_answers_migration.py BEFORE.db AFTER.db
Both files are read-only. Run only after Alembic upgrade 0007 succeeds on AFTER.db.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def _db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def audit(before: Path, after: Path) -> None:
    with _db(before) as old, _db(after) as new:
        old_rows = old.execute(
            "SELECT s.*, r.status, r.applied, r.reason, ss.user_id "
            "FROM submissions s "
            "JOIN session_items i ON i.id = s.session_item_id "
            "JOIN study_sessions ss ON ss.id = i.session_id "
            "LEFT JOIN attempt_results r ON r.submission_pk = s.id ORDER BY s.id"
        ).fetchall()
        new_rows = new.execute("SELECT * FROM answers ORDER BY id").fetchall()
        assert len(old_rows) == len(new_rows), "submission/answer count changed"
        old_results = old.execute("SELECT COUNT(*) FROM attempt_results").fetchone()[0]
        new_results = sum(row["status"] is not None for row in new_rows)
        assert old_results == new_results, "graded result count changed"
        old_labels = dict(
            old.execute(
                "SELECT hint_attempt_pk, hint_type FROM item_help_state "
                "WHERE hint_attempt_pk IS NOT NULL AND hint_type IS NOT NULL"
            ).fetchall()
        )
        sequence: dict[int, int] = {}
        labeled = 0
        for source, target in zip(old_rows, new_rows, strict=True):
            pk = source["id"]
            assert pk == target["id"], f"answer id changed at {pk}"
            for field in (
                "user_id",
                "session_item_id",
                "submission_id",
                "answer_kind",
                "status",
                "reason",
                "applied",
                "created_at",
                "reserved_revision",
                "lease",
                "leased_at",
            ):
                assert source[field] == target[field], f"{field} changed at answer {pk}"
            assert source["answer_latex"] == target["latex"], f"LaTeX changed at {pk}"
            payload = json.loads(source["answer_json"])
            mathjson = json.loads(target["mathjson"]) if target["mathjson"] is not None else None
            assert payload.get("mathjson") == mathjson, f"MathJSON changed at {pk}"
            assert payload.get("choice_id") == target["choice_id"], f"choice changed at {pk}"
            expected_attempt = None
            if source["applied"]:
                item = source["session_item_id"]
                sequence[item] = sequence.get(item, 0) + 1
                expected_attempt = sequence[item]
            assert target["attempt_no"] == expected_attempt, f"attempt order changed at {pk}"
            expected_label = old_labels.get(pk) if source["status"] == "incorrect" else None
            assert target["mistake_type"] == expected_label, f"label changed at {pk}"
            labeled += expected_label is not None
        assert new.execute("PRAGMA foreign_key_check").fetchall() == [], "foreign key error"
        print(
            f"PASS answers={len(new_rows)} graded={new_results} "
            f"items={len(sequence)} labels={labeled}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args()
    audit(args.before, args.after)
