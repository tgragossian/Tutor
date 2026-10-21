"""The JSON practice API end to end, with a spy pool."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel
from support.webapp import (
    CORRECT,
    INCORRECT,
    PASSWORD,
    ROOT,
    SpyPool,
    login,
    make_client,
    start,
)

from mathtutor.domain import FormatIssueCode
from mathtutor.verify.types import FormatIssue, VerifierBusy
from mathtutor.web import schemas

EXAMPLES = ROOT / "contracts" / "examples"


@pytest.fixture
def pool() -> SpyPool:
    return SpyPool()


@pytest.fixture
def client(tmp_path: Path, pool: SpyPool) -> Iterator[TestClient]:
    with make_client(tmp_path, pool) as c:
        yield c


@pytest.fixture
def client_logged_in(client: TestClient) -> TestClient:
    login(client)
    return client


def _current(client: TestClient, sid: int) -> dict[str, Any]:
    r = client.get(f"/api/sessions/{sid}/current")
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def _submit_body(item: dict[str, Any], answer: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "submission_id": str(uuid.uuid4()),
        "session_item_id": item["session_item_id"],
        "item_revision": item["revision"],
        "answer": answer or {"kind": "expression", "mathjson": ["Multiply", 2, "x"], "latex": "2x"},
    }


def test_full_loop_over_json(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    cur = _current(c, sid)
    assert cur["done"] is False and cur["reason"] is None
    item = cur["item"]
    assert item["allowed_actions"] == ["submit", "skip"] and item["tries_left"] == 3

    pool.script = [INCORRECT, CORRECT]
    wrong = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item))
    assert wrong.status_code == 200, wrong.text
    body = wrong.json()
    assert body["outcome"] == {
        "status": "incorrect",
        "reason": "counterexample",
        "method": "refutation",
    }
    assert body["item"]["tries_left"] == 2 and body["replayed"] is False

    right = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(body["item"]))
    assert right.json()["outcome"]["status"] == "correct"
    answered = right.json()["item"]
    assert answered["allowed_actions"] == ["advance"]

    nxt = c.post(f"/api/sessions/{sid}/advance", json={"item_revision": answered["revision"]})
    assert nxt.status_code == 200, nxt.text
    assert nxt.json()["item"]["session_item_id"] != item["session_item_id"]

    history = c.get("/api/sessions").json()
    assert history[0]["session_id"] == sid
    assert (history[0]["answered"], history[0]["correct"]) == (1, 1)


def test_stale_and_action_errors(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    stale = c.post(f"/api/sessions/{sid}/skip", json={"item_revision": item["revision"] + 5})
    assert stale.status_code == 409 and stale.json()["error"] == "stale_item"
    reveal = c.post(f"/api/sessions/{sid}/reveal", json={"item_revision": item["revision"]})
    assert reveal.status_code == 409 and reveal.json()["error"] == "invalid_action"
    assert c.get("/api/sessions/999/current").status_code == 404


def test_reveal_after_exhaustion(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    pool.script = [INCORRECT] * 3
    item = _current(c, sid)["item"]
    for _ in range(3):
        item = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item)).json()["item"]
    r = c.post(f"/api/sessions/{sid}/reveal", json={"item_revision": item["revision"]})
    assert r.status_code == 200
    assert r.json()["revealed_latex"]
    assert r.json()["item"]["allowed_actions"] == ["advance"]


def test_submit_preserves_decimal_literal(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    # json.dumps writes the float as the literal -0.5835 in the body text.
    body = _submit_body(
        item, {"kind": "expression", "mathjson": ["Multiply", -0.5835, "x"], "latex": "-0.5835x"}
    )
    text = json.dumps(body)
    assert "-0.5835," in text
    r = c.post(
        f"/api/sessions/{sid}/submit",
        content=text,
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 200, r.text
    assert pool.requests[-1].answer.mathjson == ["Multiply", {"num": "-0.5835"}, "x"]


def test_body_over_16kb_is_413(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    body = _submit_body(item)
    body["answer"]["latex"] = "x" * 17_000
    r = c.post(f"/api/sessions/{sid}/submit", json=body)
    assert r.status_code == 413
    assert r.json()["error"] == "payload_too_large"
    assert pool.requests == []


def test_body_over_16kb_without_content_length_is_413(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)

    def chunks() -> Iterator[bytes]:
        yield b'{"topics": ["'
        for _ in range(20):
            yield b"a" * 1000
        yield b'"]}'

    r = c.post("/api/sessions", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413, r.text
    assert sid  # the earlier session is unaffected


def test_kind_mismatch_is_422(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    r = c.post(
        f"/api/sessions/{sid}/submit",
        json=_submit_body(item, {"kind": "choice", "choice_id": "a"}),
    )
    assert r.status_code == 422
    assert r.json()["error"] == "kind_mismatch"
    bad = c.post(f"/api/sessions/{sid}/submit", json={"answer": "nope"})
    assert bad.status_code == 422 and set(bad.json()) == {"error", "message"}
    nan = c.post(
        f"/api/sessions/{sid}/submit",
        content='{"submission_id": NaN}',
        headers={"content-type": "application/json"},
    )
    assert nan.status_code == 422
    assert pool.requests == []


def test_too_large_tree_rejected_before_pool(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    tree = ["Add", *([1] * 200)]  # the list plus 200 terms: 201 nodes
    r = c.post(
        f"/api/sessions/{sid}/submit",
        json=_submit_body(item, {"kind": "expression", "mathjson": tree, "latex": "1+1"}),
    )
    assert r.status_code == 200, r.text
    assert r.json()["outcome"]["code"] == "input_too_large"
    assert r.json()["outcome"]["message"]
    assert r.json()["item"]["revision"] == item["revision"]
    assert pool.requests == []


def test_format_issue_messages_are_friendly(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    pool.script = [
        FormatIssue(
            FormatIssueCode.UNSUPPORTED_NOTATION, "Did you mean e·(...)? Add a multiplication sign."
        ),
        FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, "unknown symbol 'y'"),
    ]
    first = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item)).json()["outcome"]
    assert first == {
        "code": "unsupported_notation",
        "message": "Did you mean e·(...)? Add a multiplication sign.",
    }
    second = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item)).json()["outcome"]
    assert "unknown symbol" not in second["message"]
    assert second["message"]


def test_busy_is_503_with_retry_after(client_logged_in: TestClient, pool: SpyPool) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    pool.script = [VerifierBusy]
    r = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item))
    assert r.status_code == 503
    assert r.json()["error"] == "verifier_busy"
    assert r.headers["retry-after"] == "2"


def test_submit_requires_csrf(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)
    item = _current(c, sid)["item"]
    del c.headers["X-CSRF-Token"]
    r = c.post(f"/api/sessions/{sid}/submit", json=_submit_body(item))
    assert r.status_code == 403
    assert c.post("/api/sessions", json={"topics": ["derivatives.trig"]}).status_code == 403


def test_submit_rate_limit_30_per_minute(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)
    for _ in range(30):
        assert c.post(f"/api/sessions/{sid}/submit", json={}).status_code == 422
    r = c.post(f"/api/sessions/{sid}/submit", json={})
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"


def test_start_validates_topics(client_logged_in: TestClient) -> None:
    c = client_logged_in
    assert c.post("/api/sessions", json={"topics": []}).status_code == 422
    four = ["derivatives.trig"] * 4
    assert c.post("/api/sessions", json={"topics": four}).status_code == 422
    unknown = c.post("/api/sessions", json={"topics": ["derivatives.nope"]})
    assert unknown.status_code == 409 and unknown.json()["error"] == "unknown_topic"


def test_api_requires_login(client: TestClient) -> None:
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions/1/current").status_code == 401


def test_readyz_503_when_pool_dead(client: TestClient, pool: SpyPool) -> None:
    assert client.get("/readyz").status_code == 200
    pool.is_alive = False
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"status": "not_ready", "reason": "verifier_pool_down"}


def test_readyz_503_when_database_unreachable(tmp_path: Path, pool: SpyPool) -> None:
    from support.webapp import REAL_PATH

    from mathtutor.settings import Settings
    from mathtutor.web.app import create_app

    missing = tmp_path / "no" / "such" / "dir" / "db.sqlite"
    settings = Settings(
        env="test", content_path=REAL_PATH, database_url=f"sqlite:///{missing.as_posix()}"
    )
    with TestClient(create_app(settings, pool=pool)) as c:
        r = c.get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"status": "not_ready", "reason": "database_unavailable"}


def test_pool_closed_on_shutdown_only_when_owned(tmp_path: Path, pool: SpyPool) -> None:
    with make_client(tmp_path, pool):
        pass
    assert pool.closed is False  # an injected pool belongs to the caller


MODELS: dict[str, type[BaseModel]] = {
    "submit-response-": schemas.SubmitResponse,
    "submit-": schemas.SubmissionRequest,
    "item-": schemas.PublicItem,
    "start-request": schemas.StartRequest,
    "start-response": schemas.StartResponse,
    "action-request": schemas.ActionRequest,
    "current-": schemas.CurrentResponse,
    "error-": schemas.ErrorBody,
    "sessions-": schemas.SessionSummaryOut,
}


def _model_for(name: str) -> type[BaseModel]:
    for prefix, model in MODELS.items():
        if name.startswith(prefix):
            return model
    raise AssertionError(f"no model for contracts/examples/{name}")


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.json")), ids=lambda p: p.name)
def test_contract_examples_round_trip(path: Path) -> None:
    model = _model_for(path.name)
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        parsed = model.model_validate(row)
        assert json.loads(parsed.model_dump_json()) == row


def test_contract_examples_cover_new_responses() -> None:
    names = {p.name for p in EXAMPLES.glob("*.json")}
    for prefix in ("start-request", "start-response", "current-", "submit-response-", "error-"):
        assert any(n.startswith(prefix) for n in names), prefix


def test_password_and_cookie_not_in_examples() -> None:
    for path in EXAMPLES.glob("*.json"):
        assert PASSWORD not in path.read_text(encoding="utf-8")
