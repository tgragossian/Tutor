"""Review probes: assertions describe desired behavior; fail on d428bd7.

Run explicitly with pytest; these are outside the normal tests/ collection.
Only temporary SQLite databases and in-memory content copies are modified.
"""

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from support.webapp import SpyPool, login, make_client, start

from mathtutor.application.errors import StaleItem
from mathtutor.application.practice import PracticeService
from mathtutor.content.loader import LoadedContent
from mathtutor.domain import AnswerKind, FormatIssueCode
from mathtutor.store.models import SessionItem
from mathtutor.verify.types import FormatIssue, SubmittedAnswer


@pytest.fixture
def world(tmp_path):
    pool = SpyPool()
    with make_client(tmp_path, pool) as client:
        login(client)
        sid = start(client)
        item = client.get(f"/api/sessions/{sid}/current").json()["item"]
        yield client, pool, sid, item


def test_ba1_duplicate_skip_must_not_skip_next_presentation(world):
    client, _, sid, item = world
    body = {"item_revision": item["revision"]}
    first = client.post(f"/api/sessions/{sid}/skip", json=body)
    second = client.post(f"/api/sessions/{sid}/skip", json=body)
    assert first.status_code == 200
    assert second.status_code == 409, (
        "same revision applied twice to different presentations",
        first.json()["item"]["session_item_id"],
        second.json()["item"]["session_item_id"],
        second.status_code,
    )


def test_ba2_deep_json_must_not_escape_as_500(world):
    client, pool, sid, item = world
    body = json.dumps(
        {
            "submission_id": str(uuid4()),
            "session_item_id": item["session_item_id"],
            "item_revision": item["revision"],
            "answer": {"kind": "expression", "latex": "x", "mathjson": "TREE"},
        }
    ).replace('"TREE"', "[" * 5000 + '"x"' + "]" * 5000)
    assert len(body.encode()) < 16384
    with TestClient(client.app, base_url="https://testserver", raise_server_exceptions=False) as c:
        c.cookies.update(client.cookies)
        c.headers["X-CSRF-Token"] = client.headers["X-CSRF-Token"]
        result = c.post(
            f"/api/sessions/{sid}/submit",
            content=body,
            headers={"content-type": "application/json"},
        )
    assert pool.requests == []
    assert result.status_code in (200, 400, 413, 422), (result.status_code, result.text)


def test_ba3_lock_contention_must_return_busy_not_500(world):
    client, _, _, _ = world
    db_path = client.app.state.engine.url.database
    # Keep a real competing writer open beyond the configured 5-second busy timeout.
    with sqlite3.connect(db_path) as holder:
        holder.execute("BEGIN IMMEDIATE")
        try:
            with TestClient(
                client.app, base_url="https://testserver", raise_server_exceptions=False
            ) as c:
                c.cookies.update(client.cookies)
                result = c.get("/api/auth/me")
        finally:
            holder.rollback()
    assert result.status_code in (200, 503), (result.status_code, result.text)


def test_ba4_existing_presentation_must_not_silently_change_version(world):
    client, pool, sid, item = world
    content = client.app.state.content
    sessions = client.app.state.sessions
    with sessions() as db:
        stored = db.get(SessionItem, item["session_item_id"])
        problem_id, original_version = stored.item_id, stored.content_version
        user_id = stored.session.user_id
    changed = content.bundle.model_copy(deep=True)
    problem = next(p for p in changed.problems if p.id == problem_id)
    replacement = problem.model_copy(update={"statement_html": "<p>Changed after deploy</p>"})
    changed = changed.model_copy(
        update={"problems": [replacement if p.id == problem_id else p for p in changed.problems]}
    )
    current = LoadedContent(
        changed, {**content.versions, problem_id: "newversion00"}, "newbundle000"
    )
    service = PracticeService(sessions, current, pool, lambda: datetime.now(UTC))
    # A safe implementation either rejects this stale presentation or retains its snapshot.
    try:
        view = service.current_item(user_id, sid)
    except StaleItem:
        return
    with sessions() as db:
        version = db.scalar(
            select(SessionItem.content_version).where(SessionItem.id == item["session_item_id"])
        )
    assert view.statement_html == item["statement_html"], (
        "old presentation renders new content under old recorded version",
        original_version,
        version,
        view.statement_html,
    )


def test_ba5_late_format_issue_must_not_restore_completed_item(world):
    client, pool, sid, item = world
    svc = client.app.state.practice
    with client.app.state.sessions() as db:
        user_id = db.get(SessionItem, item["session_item_id"]).session.user_id
    original_submit = pool.submit

    def interleaved(req):
        svc.skip(user_id, sid, item["revision"])
        pool.default = FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, "Try another form")
        return original_submit(req)

    pool.submit = interleaved
    with pytest.raises(StaleItem):
        svc.submit_answer(
            user_id,
            sid,
            uuid4(),
            item["session_item_id"],
            item["revision"],
            SubmittedAnswer(AnswerKind.EXPRESSION, "x", "x", None),
        )
