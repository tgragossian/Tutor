"""Server-rendered pages: forms, topic picker, history, the practice shell, CSP and SRI."""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from support.webapp import PASSWORD, ROOT, SpyPool, login, make_client, start

from mathtutor.web.security import COOKIE_NAME

STATIC = ROOT / "src" / "mathtutor" / "web" / "static"
SECURITY_DOC = ROOT / "docs" / "ops" / "security.md"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with make_client(tmp_path, SpyPool()) as c:
        yield c


@pytest.fixture
def client_logged_in(client: TestClient) -> TestClient:
    login(client)
    return client


def _csrf_field(html: str) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match, "no csrf_token field"
    return match.group(1)


def test_login_register_pages_render_and_post(client: TestClient) -> None:
    for path in ("/login", "/register"):
        r = client.get(path)
        assert r.status_code == 200
        assert '<form method="post"' in r.text and 'name="password"' in r.text
    r = client.post(
        "/register", data={"username": "ada_1", "password": PASSWORD}, follow_redirects=False
    )
    assert r.status_code == 303 and r.headers["location"] == "/"
    assert COOKIE_NAME in r.cookies or COOKIE_NAME in client.cookies
    assert "ada_1" in client.get("/").text

    client.cookies.clear()
    bad = client.post("/login", data={"username": "ada_1", "password": "wrong-pass"})
    assert bad.status_code == 401
    assert "Username or password is incorrect" in bad.text
    ok = client.post(
        "/login", data={"username": "ada_1", "password": PASSWORD}, follow_redirects=False
    )
    assert ok.status_code == 303 and ok.headers["location"] == "/"


def test_register_form_errors_rerender(client: TestClient) -> None:
    r = client.post("/register", data={"username": "ab", "password": PASSWORD})
    assert r.status_code == 422
    assert "Usernames are 3–32 characters" in r.text
    assert 'value="ab"' in r.text  # the username is kept; the password is not
    assert PASSWORD not in r.text


REQUIRED_ATTRIBUTION = "Download for free at https://openstax.org/details/books/calculus-volume-1."


def test_every_page_carries_the_required_openstax_attribution(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)
    for path in ("/", f"/practice/{sid}", "/login", "/register", "/practice/999"):
        assert REQUIRED_ATTRIBUTION in c.get(path).text, path


def test_index_signed_out_links_to_login(client: TestClient) -> None:
    r = client.get("/")
    assert 'href="/login"' in r.text and 'href="/register"' in r.text
    assert 'name="topics"' not in r.text


def test_index_signed_in_shows_topics_and_history(client_logged_in: TestClient) -> None:
    c = client_logged_in
    r = c.get("/")
    assert r.text.count('name="topics"') == 3
    for topic in ("derivatives.basic_rules", "derivatives.trig", "derivatives.chain_rule"):
        assert f'value="{topic}"' in r.text
    sid = start(c)
    page = c.get("/").text
    assert f'href="/practice/{sid}"' not in page  # nothing answered yet: not history
    item = c.get(f"/api/sessions/{sid}/current").json()["item"]
    c.post(
        f"/api/sessions/{sid}/submit",
        json={
            "submission_id": "2b0c1d3e-4f5a-4b6c-8d7e-9f0a1b2c3d4e",
            "session_item_id": item["session_item_id"],
            "item_revision": item["revision"],
            "answer": {"kind": "expression", "mathjson": ["Multiply", 2, "x"], "latex": "2x"},
        },
    )
    page = c.get("/").text
    assert f'href="/practice/{sid}"' in page
    # Starting from the picker form redirects to the practice page.
    form = c.post(
        "/sessions",
        data={"topics": ["derivatives.trig"], "csrf_token": _csrf_field(page)},
        follow_redirects=False,
    )
    assert form.status_code == 303
    assert re.fullmatch(r"/practice/\d+", form.headers["location"])


def test_start_form_requires_csrf_and_topics(client_logged_in: TestClient) -> None:
    c = client_logged_in
    del c.headers["X-CSRF-Token"]
    assert c.post("/sessions", data={"topics": ["derivatives.trig"]}).status_code == 403
    token = _csrf_field(c.get("/").text)
    empty = c.post("/sessions", data={"csrf_token": token})
    assert empty.status_code == 409


def test_practice_page_requires_owner(client_logged_in: TestClient) -> None:
    c = client_logged_in
    sid = start(c)
    c.cookies.clear()
    del c.headers["X-CSRF-Token"]
    assert c.get(f"/practice/{sid}", follow_redirects=False).status_code == 303
    login(c, "mallory")
    r = c.get(f"/practice/{sid}")
    assert r.status_code == 403
    assert r.headers["content-type"].startswith("text/html")
    assert c.get("/practice/999").status_code == 404


def test_practice_page_has_csrf_meta_and_sri_scripts(client_logged_in: TestClient) -> None:
    c = client_logged_in
    csrf = c.headers["X-CSRF-Token"]
    sid = start(c)
    html = c.get(f"/practice/{sid}").text
    assert f'<meta name="csrf-token" content="{csrf}">' in html
    assert f'data-session-id="{sid}"' in html
    vendor = re.findall(r'<(?:script|link)[^>]*(?:src|href)="/static/vendor/([^"]+)"[^>]*>', html)
    assert {"mathlive/mathlive.min.mjs", "compute-engine/compute-engine.js"} <= set(vendor)
    for tag in re.findall(r"<(?:script|link)[^>]*/static/vendor/[^>]*>", html):
        path = re.search(r'(?:src|href)="/static/vendor/([^"]+)"', tag)
        integrity = re.search(r'integrity="(sha384-[^"]+)"', tag)
        assert path and integrity, tag
        digest = hashlib.sha384((STATIC / "vendor" / path.group(1)).read_bytes()).digest()
        assert integrity.group(1) == "sha384-" + base64.b64encode(digest).decode()
    assert re.search(r'<script type="module" src="/static/practice.js', html)
    assert "<script>" not in html  # no inline scripts


def test_static_files_served(client: TestClient) -> None:
    for path in ("/static/practice.js", "/static/app.css", "/static/vendor/manifest.json"):
        assert client.get(path).status_code == 200, path


def _documented_csp() -> str:
    match = re.search(r"Content-Security-Policy: (.+)", SECURITY_DOC.read_text(encoding="utf-8"))
    assert match, "docs/ops/security.md must record the CSP"
    return match.group(1).strip().strip("`")


def test_pages_send_csp(client: TestClient) -> None:
    expected = _documented_csp()
    assert "script-src 'self'" in expected or expected.startswith("default-src 'self'")
    assert "unsafe-eval" not in expected
    for path in ("/", "/login", "/register", "/healthz"):
        assert client.get(path).headers["content-security-policy"] == expected


def test_logout_form_requires_csrf(client_logged_in: TestClient) -> None:
    c = client_logged_in
    page = c.get("/").text
    token = _csrf_field(page)
    del c.headers["X-CSRF-Token"]
    assert c.post("/logout").status_code == 403
    assert c.get("/api/auth/me").status_code == 200
    r = c.post("/logout", data={"csrf_token": token}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert c.get("/api/auth/me").status_code == 401


def test_pages_rate_limited(client: TestClient) -> None:
    for _ in range(10):
        client.post("/login", data={"username": "nobody", "password": "wrong-pass"})
    r = client.post("/login", data={"username": "nobody", "password": "wrong-pass"})
    assert r.status_code == 429
