"""POST /api/help, help availability on items, history clearing and the follow-up link."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from support.webapp import INCORRECT, ROOT, SpyPool, login, make_settings, start

from mathtutor.domain import FormatIssueCode
from mathtutor.help import messages
from mathtutor.help.generator import GenerationRequest, GenerationResult, ScriptedGenerator
from mathtutor.store.models import HelpRequestRow, ItemHelpState, Submission, UsageEntry, User
from mathtutor.verify.types import FormatIssue
from mathtutor.web.app import create_app

CORPUS = ROOT / "content" / "corpus" / "chunks.jsonl"
HINT = "Work from the outside in: name the outer function first, then the inner one."
WRONG_LATEX = "7777q"


class CitingGenerator(ScriptedGenerator):
    """Cites the first retrieved passage; ``gate`` (if set) blocks each call until released."""

    def __init__(self, text: str = HINT) -> None:
        super().__init__([])
        self.text = text
        self.gate: threading.Event | None = None
        self.entered = threading.Event()

    def generate(self, req: GenerationRequest) -> GenerationResult:
        self.requests.append(req)
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(10)
        ids = re.findall(r'<passage id="([^"]+)"', req.user)[:1]
        body = json.dumps({"text": self.text, "source_ids": ids, "abstain": False})
        return GenerationResult(body, "end_turn", 2000, 300, req.model, "req_t", 5)


def _app(
    tmp_path: Path, generator: ScriptedGenerator | None = None, **update: Any
) -> tuple[FastAPI, SpyPool]:
    settings = make_settings(tmp_path).model_copy(
        update={"help_generator": "scripted", "corpus_path": CORPUS, **update}
    )
    pool = SpyPool()
    pool.default = INCORRECT
    guard = SpyPool()
    guard.default = INCORRECT  # every candidate differs from the answer: no leak
    app = create_app(settings, pool=pool, guard_pool=guard, generator=generator)
    return app, pool


@pytest.fixture
def gen() -> CitingGenerator:
    return CitingGenerator()


@pytest.fixture
def app_pool(tmp_path: Path, gen: CitingGenerator) -> tuple[FastAPI, SpyPool]:
    return _app(tmp_path, gen)


@pytest.fixture
def client(app_pool: tuple[FastAPI, SpyPool]) -> Iterator[TestClient]:
    with TestClient(app_pool[0], base_url="https://testserver") as c:
        login(c)
        yield c


def _item(c: TestClient, sid: int) -> dict[str, Any]:
    r = c.get(f"/api/sessions/{sid}/current")
    assert r.status_code == 200, r.text
    item: dict[str, Any] = r.json()["item"]
    return item


def _help(
    c: TestClient, item: dict[str, Any], help_type: str = "hint", **extra: Any
) -> dict[str, Any]:
    return {
        "help_request_id": str(uuid.uuid4()),
        "session_item_id": item["session_item_id"],
        "item_revision": item["revision"],
        "help_type": help_type,
        "confusion": None,
        **extra,
    }


def _submit(c: TestClient, sid: int, item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sub_id = str(uuid.uuid4())
    body = {
        "submission_id": sub_id,
        "session_item_id": item["session_item_id"],
        "item_revision": item["revision"],
        "answer": {"kind": "expression", "mathjson": ["Multiply", 7777, "q"], "latex": WRONG_LATEX},
    }
    r = c.post(f"/api/sessions/{sid}/submit", json=body)
    assert r.status_code == 200, r.text
    return sub_id, r.json()


def _rows(app: FastAPI) -> list[HelpRequestRow]:
    with app.state.sessions() as db:
        return list(db.scalars(select(HelpRequestRow).order_by(HelpRequestRow.id)))


def test_item_carries_help_availability(client: TestClient) -> None:
    sid = start(client)
    help_ = _item(client, sid)["help"]
    assert help_["enabled"] is True and help_["hint_level"] == 1
    assert help_["types"][0] == "hint" and "feedback" not in help_["types"]
    assert all(set(c) == {"id", "label"} for c in help_["confusions"])


def test_hint_delivered(client: TestClient, gen: CitingGenerator) -> None:
    sid = start(client)
    item = _item(client, sid)
    r = client.post("/api/help", json=_help(client, item))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "delivered" and body["hint_level"] == 1 and body["help_seq"] == 1
    assert "outside in" in body["html"] and len(body["sources"]) == 1
    assert set(body["sources"][0]) == {"label", "url", "license"}
    assert _item(client, sid)["help"]["hint_level"] == 2
    assert len(gen.requests) == 1


def test_help_requires_csrf_and_owner(app_pool: tuple[FastAPI, SpyPool]) -> None:
    app = app_pool[0]
    with TestClient(app, base_url="https://testserver") as alice:
        login(alice, "alice_1")
        item = _item(alice, start(alice))
        token = alice.headers.pop("X-CSRF-Token")
        r = alice.post("/api/help", json=_help(alice, item))
        assert r.status_code == 403 and r.json()["error"] == "csrf_failed"
        alice.headers["X-CSRF-Token"] = token
    with TestClient(app, base_url="https://testserver") as bob:
        login(bob, "bob_1")
        r = bob.post("/api/help", json=_help(bob, item))
        assert r.status_code == 404 and r.json()["error"] == "not_found"
        missing = {**_help(bob, item), "session_item_id": 99999}
        assert bob.post("/api/help", json=missing).status_code == 404
    assert _rows(app) == []


def test_question_type_rejected_in_c1(client: TestClient) -> None:
    item = _item(client, start(client))
    r = client.post("/api/help", json=_help(client, item, "question"))
    assert r.status_code == 422 and r.json()["error"] == "invalid_request"
    extra = {**_help(client, item), "free_text": "why?"}
    assert client.post("/api/help", json=extra).status_code == 422


def test_stale_revision_and_reused_id_are_409(client: TestClient) -> None:
    item = _item(client, start(client))
    stale = client.post("/api/help", json=_help(client, item, item_revision=item["revision"] + 3))
    assert stale.status_code == 409 and stale.json()["error"] == "stale_item"
    first = _help(client, item)
    assert client.post("/api/help", json=first).status_code == 200
    replay = client.post("/api/help", json=first)
    assert replay.status_code == 200 and replay.json()["status"] == "delivered"
    reused = client.post("/api/help", json={**first, "help_type": "explain", "confusion": "x_y"})
    assert reused.status_code == 409 and reused.json()["error"] == "conflict"


def test_feedback_without_wrong_answer_is_409(client: TestClient) -> None:
    item = _item(client, start(client))
    r = client.post("/api/help", json=_help(client, item, "feedback"))
    assert r.status_code == 409 and r.json()["error"] == "no_wrong_attempt"


def test_pending_is_202(app_pool: tuple[FastAPI, SpyPool], gen: CitingGenerator) -> None:
    gen.gate = threading.Event()
    with TestClient(app_pool[0], base_url="https://testserver") as c:
        login(c)
        item = _item(c, start(c))
        first = _help(c, item)
        got: list[Any] = []
        worker = threading.Thread(target=lambda: got.append(c.post("/api/help", json=first)))
        worker.start()
        assert gen.entered.wait(10)
        r = c.post("/api/help", json=_help(c, item))
        gen.gate.set()
        worker.join(10)
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "pending" and r.json()["request_id"] == first["help_request_id"]
    assert got[0].status_code == 200 and got[0].json()["status"] == "delivered"


def test_help_limited_is_429(tmp_path: Path, gen: CitingGenerator) -> None:
    cfg = json.loads((ROOT / "src/mathtutor/help/help_config.json").read_text(encoding="utf-8"))
    cfg["admission"]["per_hour"] = 1
    path = tmp_path / "help_config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    app, _ = _app(tmp_path, gen, help_config_path=path)
    with TestClient(app, base_url="https://testserver") as c:
        login(c)
        sid = start(c)
        assert c.post("/api/help", json=_help(c, _item(c, sid))).status_code == 200
        r = c.post("/api/help", json=_help(c, _item(c, sid)))
    assert r.status_code == 429
    assert r.json() == {"error": "help_limited", "message": messages.LIMITED}


def test_readyz_ready_without_help(tmp_path: Path) -> None:
    """Claude selected but no API key: help is off, the app is ready, items carry null."""
    settings = make_settings(tmp_path).model_copy(
        update={"help_generator": "claude", "anthropic_api_key": None, "corpus_path": CORPUS}
    )
    app = create_app(settings, pool=SpyPool(), guard_pool=SpyPool())
    with TestClient(app, base_url="https://testserver") as c:
        assert c.get("/readyz").status_code == 200
        login(c)
        item = _item(c, start(c))
        assert item["help"] is None
        r = c.post("/api/help", json=_help(c, item))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unavailable" and messages.UNAVAILABLE in body["html"]
    assert body["sources"] == [] and _rows(app) == []


@pytest.mark.parametrize(
    "update",
    [
        {"help_generator": "off"},
        {"help_generator": "claude", "anthropic_api_key": None},
        {"help_generator": "scripted", "corpus_path": Path("missing/chunks.jsonl")},
    ],
    ids=["off", "no_key", "no_corpus"],
)
def test_help_disabled_starts_no_guard_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, update: dict[str, Any]
) -> None:
    made: list[SpyPool] = []

    def fake_pool(**_kwargs: object) -> SpyPool:
        made.append(SpyPool())
        return made[-1]

    monkeypatch.setattr("mathtutor.web.app.VerifierPool", fake_pool)
    settings = make_settings(tmp_path).model_copy(update={"corpus_path": CORPUS, **update})
    app = create_app(settings)
    with TestClient(app) as c:
        assert c.get("/readyz").status_code == 200
        assert len(made) == 1 and app.state.guard_pool is None
        assert app.state.help.enabled is False


def test_claude_with_key_enables_help(tmp_path: Path) -> None:
    settings = make_settings(tmp_path).model_copy(
        update={
            "help_generator": "claude",
            "anthropic_api_key": SecretStr("sk-test"),
            "corpus_path": CORPUS,
        }
    )
    app = create_app(settings, pool=SpyPool(), guard_pool=SpyPool())
    assert app.state.help.enabled is True


def test_clear_history_removes_help_text_keeps_usage(
    client: TestClient, app_pool: tuple[FastAPI, SpyPool]
) -> None:
    app = app_pool[0]
    sid = start(client)
    item = _item(client, sid)
    req = _help(client, item)
    assert client.post("/api/help", json=req).json()["status"] == "delivered"
    with app.state.sessions() as db:
        usage_before = [(u.id, u.state, u.settled_micros) for u in db.scalars(select(UsageEntry))]
    assert _rows(app)[0].output_json is not None
    token = client.headers["X-CSRF-Token"]
    r = client.post("/history/clear", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303
    (row,) = _rows(app)
    assert row.output_json is None and row.cleared_at is not None and row.status == "delivered"
    with app.state.sessions() as db:
        user = db.get(User, row.user_id)
        assert user is not None and user.privacy_epoch == 1
        assert [
            (u.id, u.state, u.settled_micros) for u in db.scalars(select(UsageEntry))
        ] == usage_before
    replay = client.post("/api/help", json=req).json()
    assert replay["status"] == "stale" and replay["html"] is None and replay["sources"] == []


def test_next_attempt_linked_once(client: TestClient, app_pool: tuple[FastAPI, SpyPool]) -> None:
    app, pool = app_pool
    sid = start(client)
    item = _item(client, sid)
    assert client.post("/api/help", json=_help(client, item)).json()["status"] == "delivered"
    # A format issue changes nothing, so it is not the follow-up attempt.
    pool.script = [FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, "")]
    _submit(client, sid, item)
    assert _rows(app)[0].next_submission_id is None
    first, body = _submit(client, sid, item)
    _submit(client, sid, body["item"])
    (row,) = _rows(app)
    assert row.next_submission_id == first
    with app.state.sessions() as db:
        assert db.scalar(select(Submission).where(Submission.submission_id == first)) is not None


def test_in_flight_cleared_after_help(client: TestClient, app_pool: Any) -> None:
    app = app_pool[0]
    item = _item(client, start(client))
    client.post("/api/help", json=_help(client, item))
    with app.state.sessions() as db:
        state = db.get(ItemHelpState, item["session_item_id"])
        assert state is not None and state.in_flight is None


def test_logs_have_no_student_or_model_text(
    client: TestClient,
    gen: CitingGenerator,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sid = start(client)
    item = _item(client, sid)
    _, body = _submit(client, sid, item)
    capsys.readouterr()
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/help", json=_help(client, body["item"], "feedback"))
        assert r.status_code == 200 and r.json()["status"] == "delivered", r.text
    req = gen.requests[-1]
    assert WRONG_LATEX in req.user  # the student's answer did reach the prompt
    chunk_id = re.findall(r'<passage id="([^"]+)"', req.user)[0]
    chunk_text = re.search(
        rf'<passage id="{re.escape(chunk_id)}"[^>]*>\n(.*?)\n</passage>', req.user, re.S
    )
    assert chunk_text is not None
    logged = caplog.text + capsys.readouterr().err
    assert '"help_status": "delivered"' in logged
    for secret in (WRONG_LATEX, HINT, "outside in", chunk_text.group(1)[:40]):
        assert secret not in logged
