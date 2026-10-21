"""One JSON log line per request, with verdict fields on submit and no secrets."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from support.webapp import CORRECT, PASSWORD, SpyPool, login, make_client, start

from mathtutor.web.security import COOKIE_NAME


def _lines(text: str) -> list[dict[str, Any]]:
    out = []
    for line in text.splitlines():
        if line.startswith("{"):
            out.append(json.loads(line))
    return out


def test_request_log_is_json_without_secrets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pool = SpyPool()
    pool.script = [CORRECT]
    with make_client(tmp_path, pool) as c:
        csrf = login(c)
        sid = start(c)
        item = c.get(f"/api/sessions/{sid}/current").json()["item"]
        r = c.post(
            f"/api/sessions/{sid}/submit",
            json={
                "submission_id": str(uuid.uuid4()),
                "session_item_id": item["session_item_id"],
                "item_revision": item["revision"],
                "answer": {"kind": "expression", "mathjson": ["Multiply", 7, "x"], "latex": "7x"},
            },
        )
        assert r.status_code == 200
        request_id = r.headers["x-request-id"]
        cookie = c.cookies[COOKIE_NAME]
    captured = capsys.readouterr()
    text = captured.out + captured.err
    lines = _lines(text)
    submit = [ln for ln in lines if ln.get("route") == "/api/sessions/{session_id}/submit"]
    assert len(submit) == 1
    entry = submit[0]
    assert entry["request_id"] == request_id and len(request_id) == 32
    assert entry["method"] == "POST" and entry["status"] == 200
    assert isinstance(entry["duration_ms"], int | float)
    assert entry["verdict_status"] == "correct"
    assert (entry["verdict_reason"], entry["verdict_method"]) == ("proven", "symbolic")
    assert (entry["worker_ms"], entry["queue_ms"]) == (5, 1)
    assert any(ln.get("route") == "/api/auth/register" and ln["status"] == 200 for ln in lines)
    for secret in (PASSWORD, csrf, cookie, '"7x"', "Multiply"):
        assert secret not in text, secret
