"""No response carries a private answer field (spec 02, spec 07 DTOs)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from support.webapp import CORRECT, INCORRECT, REAL_PATH, SpyPool, login, make_client, start

from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import ChoiceAnswer
from mathtutor.web.security import RateLimiter

CONTENT = load_bundle(REAL_PATH)
SECRET_LATEX = [
    p.answer.latex
    for p in CONTENT.bundle.problems
    if not isinstance(p.answer, ChoiceAnswer) and len(p.answer.latex) >= 4
]
SECRET_JSON = [
    s
    for p in CONTENT.bundle.problems
    if not isinstance(p.answer, ChoiceAnswer)
    for s in (
        json.dumps(p.answer.mathjson),
        json.dumps(p.answer.mathjson, separators=(",", ":")),
    )
]
PRIVATE_KEYS = {
    "correct",
    "misconceptions",
    "misconceptions_mathjson",
    "review",
    "mathjson",
    "latex",
}


def _keys(value: Any) -> set[str]:
    """Every key in a JSON tree, except ``correct`` holding a count (session history)."""
    if isinstance(value, dict):
        found = {k for k, v in value.items() if not (k == "correct" and type(v) is int)}
        for v in value.values():
            found |= _keys(v)
        return found
    if isinstance(value, list):
        return set().union(*(_keys(v) for v in value)) if value else set()
    return set()


def _assert_clean(text: str, *, allow_reveal: bool = False) -> None:
    body = json.loads(text) if text and text[0] in "[{" else None
    if body is not None:
        keys = _keys(body)
        assert not keys & PRIVATE_KEYS, keys & PRIVATE_KEYS
        if allow_reveal and isinstance(body, dict):
            body = {**body, "revealed_latex": None}
            text = json.dumps(body)
    for secret in SECRET_LATEX:
        assert secret not in text and json.dumps(secret)[1:-1] not in text, secret
    for secret in SECRET_JSON:
        assert secret not in text


def test_no_private_fields_anywhere(tmp_path: Path) -> None:
    pool = SpyPool()
    responses: list[tuple[str, bool]] = []
    with make_client(tmp_path, pool) as c:
        c.app.state.submit_limiter = RateLimiter(10_000, 60)  # this walk submits ~100 times
        login(c)
        for topics in (
            ["derivatives.basic_rules"],
            ["derivatives.trig"],
            ["derivatives.chain_rule"],
        ):
            sid = start(c, topics)
            for _ in range(12):
                cur = c.get(f"/api/sessions/{sid}/current")
                responses.append((cur.text, False))
                body = cur.json()
                if body["done"]:
                    break
                item = body["item"]
                answer: dict[str, Any] = (
                    {"kind": "choice", "choice_id": "a"}
                    if item["answer_kind"] == "choice"
                    else {
                        "kind": item["answer_kind"],
                        "mathjson": ["Multiply", 2, "x"],
                        "latex": "2x",
                    }
                )
                pool.script = [INCORRECT] * 3
                for _ in range(3):
                    r = c.post(
                        f"/api/sessions/{sid}/submit",
                        json={
                            "submission_id": str(uuid.uuid4()),
                            "session_item_id": item["session_item_id"],
                            "item_revision": item["revision"],
                            "answer": answer,
                        },
                    )
                    responses.append((r.text, False))
                    item = r.json()["item"]
                rev = c.post(
                    f"/api/sessions/{sid}/reveal", json={"item_revision": item["revision"]}
                )
                responses.append((rev.text, True))
                assert rev.json()["revealed_latex"]
                pool.script = [CORRECT]
                adv = c.post(
                    f"/api/sessions/{sid}/advance",
                    json={"item_revision": rev.json()["item"]["revision"]},
                )
                responses.append((adv.text, False))
        responses.append((c.get("/api/sessions").text, False))
        responses.append((c.get("/api/auth/me").text, False))
        for path in ("/", "/healthz", "/readyz"):
            responses.append((c.get(path).text, False))
    assert len(responses) > 20
    for text, allow_reveal in responses:
        _assert_clean(text, allow_reveal=allow_reveal)
