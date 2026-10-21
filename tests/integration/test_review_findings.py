"""Regressions for the 2026-10-21 milestone B review (B-A1..B-A5), from Codex's probes.

See docs/reviews/2026-10-21-milestone-b/.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from support.webapp import INCORRECT, SpyPool, login, make_client, start

from mathtutor.application.auth import AuthService
from mathtutor.application.errors import StaleItem
from mathtutor.application.practice import ItemView, PracticeService
from mathtutor.content.loader import LoadedContent
from mathtutor.domain import AnswerKind, FormatIssueCode
from mathtutor.store.models import SessionItem
from mathtutor.verify.types import CheckRequest, CheckResult, FormatIssue, SubmittedAnswer

World = tuple[TestClient, SpyPool, int, dict[str, Any]]


@pytest.fixture
def world(tmp_path: Path) -> Iterator[World]:
    pool = SpyPool()
    with make_client(tmp_path, pool) as client:
        login(client)
        sid = start(client)
        item = client.get(f"/api/sessions/{sid}/current").json()["item"]
        yield client, pool, sid, item


def _action(item: dict[str, Any]) -> dict[str, int]:
    return {"session_item_id": item["session_item_id"], "item_revision": item["revision"]}


def _user_id(client: TestClient, session_item_id: int) -> int:
    with client.app.state.sessions() as db:  # type: ignore[attr-defined]
        user_id: int = db.get(SessionItem, session_item_id).session.user_id
    return user_id


# -- B-A1: actions are bound to a presentation ------------------------------------------------


def test_ba1_duplicate_skip_is_stale(world: World) -> None:
    client, _, sid, item = world
    first = client.post(f"/api/sessions/{sid}/skip", json=_action(item))
    second = client.post(f"/api/sessions/{sid}/skip", json=_action(item))
    assert first.status_code == 200
    assert second.status_code == 409 and second.json()["error"] == "stale_item"
    current = client.get(f"/api/sessions/{sid}/current").json()["item"]
    assert current["session_item_id"] == first.json()["item"]["session_item_id"]


def test_ba1_delayed_advance_and_reveal_cannot_touch_the_next_item(
    world: World,
) -> None:
    client, pool, sid, item = world
    pool.script = [INCORRECT] * 3
    for _ in range(3):
        body = {
            "submission_id": str(uuid4()),
            **_action(item),
            "answer": {"kind": "expression", "mathjson": ["Multiply", 2, "x"], "latex": "2x"},
        }
        item = client.post(f"/api/sessions/{sid}/submit", json=body).json()["item"]
    exhausted = item
    nxt = client.post(f"/api/sessions/{sid}/advance", json=_action(exhausted)).json()["item"]
    # The next item is active at revision 0; replays aimed at the old one must not land.
    for action in ("advance", "reveal", "skip"):
        r = client.post(f"/api/sessions/{sid}/{action}", json=_action(exhausted))
        assert r.status_code == 409, action
    still = client.get(f"/api/sessions/{sid}/current").json()["item"]
    assert (still["session_item_id"], still["revision"]) == (nxt["session_item_id"], 0)


def test_ba1_concurrent_duplicate_skips_one_wins(world: World) -> None:
    client, _, sid, item = world
    svc: PracticeService = client.app.state.practice  # type: ignore[attr-defined]
    user_id = _user_id(client, item["session_item_id"])
    results: list[object] = []
    barrier = threading.Barrier(4)

    def skip() -> None:
        barrier.wait()
        try:
            results.append(svc.skip(user_id, sid, item["session_item_id"], item["revision"]))
        except StaleItem as exc:
            results.append(exc)

    threads = [threading.Thread(target=skip) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert sum(isinstance(r, ItemView) for r in results) == 1
    assert sum(isinstance(r, StaleItem) for r in results) == 3


# -- B-A2: deep JSON is rejected before parsing -------------------------------------------------


@pytest.mark.parametrize("opener,closer", [("[", "]"), ('{"a":', "}")])
def test_ba2_deep_json_is_422(world: World, opener: str, closer: str) -> None:
    client, pool, sid, item = world
    n = 3000 if opener == "[" else 2000  # stay under the 16 KB body cap
    tree = opener * n + '"x"' + closer * n
    body = json.dumps(
        {
            "submission_id": str(uuid4()),
            "session_item_id": item["session_item_id"],
            "item_revision": item["revision"],
            "answer": {"kind": "expression", "latex": "x", "mathjson": "TREE"},
        }
    ).replace('"TREE"', tree)
    assert len(body.encode()) < 16 * 1024
    with TestClient(client.app, base_url="https://testserver", raise_server_exceptions=False) as c:
        c.cookies.update(client.cookies)
        c.headers["X-CSRF-Token"] = client.headers["X-CSRF-Token"]
        r = c.post(
            f"/api/sessions/{sid}/submit",
            content=body,
            headers={"content-type": "application/json"},
        )
    assert r.status_code == 422, r.text
    assert r.json()["error"] == "invalid_request"
    assert "nested" in r.json()["message"]
    assert pool.requests == []


def test_ba2_brackets_inside_strings_do_not_count(world: World) -> None:
    client, pool, sid, item = world
    body = {
        "submission_id": str(uuid4()),
        **_action(item),
        "answer": {"kind": "expression", "mathjson": ["Multiply", 2, "x"], "latex": "[" * 500},
    }
    r = client.post(f"/api/sessions/{sid}/submit", json=body)
    assert r.status_code == 200, r.text
    assert len(pool.requests) == 1


# -- B-A3: lock contention never escapes as 500 ---------------------------------------------------


def test_ba3_reads_and_writes_under_a_held_write_lock(world: World) -> None:
    client, _, sid, item = world
    db_path = client.app.state.engine.url.database  # type: ignore[attr-defined]
    holder = sqlite3.connect(db_path, isolation_level=None)
    holder.execute("BEGIN IMMEDIATE")
    try:
        with TestClient(
            client.app, base_url="https://testserver", raise_server_exceptions=False
        ) as c:
            c.cookies.update(client.cookies)
            c.headers["X-CSRF-Token"] = client.headers["X-CSRF-Token"]
            # Reads do not wait for the writer (WAL readers need no lock).
            started = time.monotonic()
            assert c.get("/api/auth/me").status_code == 200
            assert c.get(f"/api/sessions/{sid}/current").status_code == 200
            assert c.get("/api/sessions").status_code == 200
            assert c.get("/").status_code == 200
            assert time.monotonic() - started < 3
            # A write waits busy_timeout, then reports a controlled 503.
            r = c.post(f"/api/sessions/{sid}/skip", json=_action(item))
            assert r.status_code == 503, r.text
            assert r.json()["error"] == "database_busy"
            assert r.headers["retry-after"] == "2"
    finally:
        holder.rollback()
        holder.close()
    # Recovery once the lock clears.
    assert client.post(f"/api/sessions/{sid}/skip", json=_action(item)).status_code == 200


def test_ba3_login_under_a_held_write_lock_is_503(tmp_path: Path) -> None:
    with make_client(tmp_path, SpyPool()) as client:
        login(client, "lockme")
        client.cookies.clear()
        db_path = client.app.state.engine.url.database  # type: ignore[attr-defined]
        holder = sqlite3.connect(db_path, isolation_level=None)
        holder.execute("BEGIN IMMEDIATE")
        try:
            with TestClient(
                client.app, base_url="https://testserver", raise_server_exceptions=False
            ) as c:
                r = c.post(
                    "/api/auth/login",
                    json={"username": "lockme", "password": "correct horse battery"},
                )
                assert r.status_code == 503, r.text
                page = c.post(
                    "/login", data={"username": "lockme", "password": "correct horse battery"}
                )
                assert page.status_code == 503
                assert page.headers["content-type"].startswith("text/html")
        finally:
            holder.rollback()
            holder.close()


# -- B-A4: a presentation keeps the content it was served with ----------------------------------


def _edited(content: LoadedContent, problem_id: str, drop: bool = False) -> LoadedContent:
    bundle = content.bundle.model_copy(deep=True)
    problem = next(p for p in bundle.problems if p.id == problem_id)
    answer = problem.answer.model_copy(update={"latex": "\\text{changed}"})
    replacement = problem.model_copy(
        update={"statement_html": "<p>Changed after deploy</p>", "answer": answer}
    )
    problems = [p for p in bundle.problems if p.id != problem_id]
    if not drop:
        problems.append(replacement)
    bundle = bundle.model_copy(update={"problems": problems})
    versions = {**content.versions, problem_id: "newversion00"}
    if drop:
        del versions[problem_id]
    return LoadedContent(bundle, versions, "newbundle000")


@pytest.mark.parametrize("drop", [False, True], ids=["edited", "removed"])
def test_ba4_presentation_keeps_its_snapshot(world: World, drop: bool) -> None:
    client, pool, sid, item = world
    old: PracticeService = client.app.state.practice  # type: ignore[attr-defined]
    user_id = _user_id(client, item["session_item_id"])
    with client.app.state.sessions() as db:  # type: ignore[attr-defined]
        stored = db.get(SessionItem, item["session_item_id"])
        problem_id, version = stored.item_id, stored.content_version
    original_answer = next(
        p.answer
        for p in client.app.state.content.bundle.problems
        if p.id == problem_id  # type: ignore[attr-defined]
    )
    content = _edited(client.app.state.content, problem_id, drop)  # type: ignore[attr-defined]
    svc = PracticeService(
        client.app.state.sessions,
        content,
        pool,
        lambda: datetime.now(UTC),  # type: ignore[attr-defined]
    )
    view = svc.current_item(user_id, sid)
    assert isinstance(view, ItemView)
    assert view.statement_html == item["statement_html"]
    pool.script = [INCORRECT] * 3
    answer = SubmittedAnswer(AnswerKind.EXPRESSION, ["Multiply", 2, "x"], "2x", None)
    for _ in range(3):
        view = svc.submit_answer(
            user_id, sid, uuid4(), view.session_item_id, view.revision, answer
        ).item
    assert pool.requests[-1].answer_spec == original_answer  # graded against the snapshot
    revealed = svc.reveal(user_id, sid, view.session_item_id, view.revision)
    assert isinstance(revealed, ItemView)
    assert revealed.revealed_latex == original_answer.latex  # type: ignore[union-attr]
    with client.app.state.sessions() as db:  # type: ignore[attr-defined]
        assert db.get(SessionItem, item["session_item_id"]).content_version == version
    assert old is not svc


def test_ba4_new_presentations_use_new_content(world: World) -> None:
    client, pool, _, item = world
    with client.app.state.sessions() as db:  # type: ignore[attr-defined]
        problem_id = db.get(SessionItem, item["session_item_id"]).item_id
    content = _edited(client.app.state.content, problem_id)  # type: ignore[attr-defined]
    sessions = client.app.state.sessions  # type: ignore[attr-defined]
    svc = PracticeService(sessions, content, pool, lambda: datetime.now(UTC))
    other = AuthService(sessions, lambda: datetime.now(UTC)).register("newcomer", "password-1")
    fresh = svc.start_session(other.user_id, ["derivatives.basic_rules"])
    view = svc.current_item(other.user_id, fresh)
    assert isinstance(view, ItemView)
    assert view.item_id == problem_id
    assert view.statement_html == "<p>Changed after deploy</p>"
    with sessions() as db:
        assert db.get(SessionItem, view.session_item_id).content_version == "newversion00"


# -- B-A5: a late format issue cannot restore an obsolete item -----------------------------------


def test_ba5_format_issue_after_skip_is_stale(world: World) -> None:
    client, pool, sid, item = world
    svc: PracticeService = client.app.state.practice  # type: ignore[attr-defined]
    user_id = _user_id(client, item["session_item_id"])
    original = pool.submit

    def interleaved(req: CheckRequest) -> CheckResult:
        svc.skip(user_id, sid, item["session_item_id"], item["revision"])
        pool.default = FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, "Try another form")
        return original(req)

    pool.submit = interleaved  # type: ignore[method-assign]
    with pytest.raises(StaleItem):
        svc.submit_answer(
            user_id,
            sid,
            uuid4(),
            item["session_item_id"],
            item["revision"],
            SubmittedAnswer(AnswerKind.EXPRESSION, "x", "x", None),
        )
