"""Auth JSON routes: cookie sessions, rotation, logout, CSRF and rate limits."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mathtutor.settings import Settings
from mathtutor.store.db import upgrade
from mathtutor.web.app import create_app
from mathtutor.web.security import COOKIE_NAME

ROOT = Path(__file__).resolve().parents[2]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
SECRET = "s" * 40
PASSWORD = "correct horse battery"


def _settings(tmp_path: Path, env: str = "test") -> Settings:
    url = f"sqlite:///{(tmp_path / 'web.db').as_posix()}"
    upgrade(url)
    return Settings(env=env, content_path=REAL_PATH, database_url=url, secret_key=SECRET)  # type: ignore[arg-type]


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(_settings(tmp_path)), base_url="https://testserver") as c:
        yield c


def _register(client: TestClient, username: str = "ada_1") -> dict[str, str]:
    r = client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()


def _with_cookie(client: TestClient, value: str) -> None:
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, value)


def test_register_me_and_login(client: TestClient) -> None:
    body = _register(client)
    assert body["username"] == "ada_1"
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"username": "ada_1", "csrf_token": body["csrf_token"]}
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401
    r = client.post("/api/auth/login", json={"username": "ada_1", "password": PASSWORD})
    assert r.status_code == 200
    assert client.get("/api/auth/me").json()["username"] == "ada_1"


def test_errors_use_error_message_shape(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": "nobody", "password": PASSWORD})
    assert r.status_code == 401
    assert set(r.json()) == {"error", "message"}
    _register(client)
    client.cookies.clear()
    dup = client.post("/api/auth/register", json={"username": "ada_1", "password": PASSWORD})
    assert dup.status_code == 409
    assert dup.json()["error"] == "username_taken"
    short = client.post("/api/auth/register", json={"username": "bob", "password": "short"})
    assert short.status_code == 422
    assert set(short.json()) == {"error", "message"}


def test_login_rotates_session(client: TestClient) -> None:
    _register(client)
    old = client.cookies[COOKIE_NAME]
    r = client.post("/api/auth/login", json={"username": "ada_1", "password": PASSWORD})
    assert r.status_code == 200
    new = client.cookies[COOKIE_NAME]
    assert new != old
    assert client.get("/api/auth/me").status_code == 200
    _with_cookie(client, old)
    assert client.get("/api/auth/me").status_code == 401


def test_logout_clears_server_side(client: TestClient) -> None:
    csrf = _register(client)["csrf_token"]
    old = client.cookies[COOKIE_NAME]
    r = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert r.status_code == 200
    assert COOKIE_NAME not in client.cookies
    _with_cookie(client, old)
    assert client.get("/api/auth/me").status_code == 401


def test_post_without_csrf_is_403(client: TestClient) -> None:
    _register(client)
    r = client.post("/api/auth/logout")
    assert r.status_code == 403
    assert r.json()["error"] == "csrf_failed"
    bad = client.post("/api/auth/logout", headers={"X-CSRF-Token": "wrong"})
    assert bad.status_code == 403
    assert client.get("/api/auth/me").status_code == 200


def test_csrf_form_field_accepted(client: TestClient) -> None:
    csrf = _register(client)["csrf_token"]
    r = client.post("/api/auth/logout", data={"csrf_token": csrf})
    assert r.status_code == 200


def test_tampered_cookie_is_401(client: TestClient) -> None:
    _register(client)
    _with_cookie(client, client.cookies[COOKIE_NAME] + "x")
    assert client.get("/api/auth/me").status_code == 401


def _set_cookie(response_headers: list[str]) -> str:
    [cookie] = [h for h in response_headers if h.startswith(f"{COOKIE_NAME}=")]
    return cookie.lower()


def test_cookie_flags(client: TestClient, tmp_path: Path) -> None:
    r = client.post("/api/auth/register", json={"username": "ada_1", "password": PASSWORD})
    cookie = _set_cookie(r.headers.get_list("set-cookie"))
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "max-age=1209600" in cookie
    assert "path=/" in cookie
    assert "; secure" in cookie  # every env except development

    dev_path = tmp_path / "dev"
    dev_path.mkdir()
    with TestClient(create_app(_settings(dev_path, env="development"))) as dev:
        r = dev.post("/api/auth/register", json={"username": "ada_1", "password": PASSWORD})
        assert "secure" not in _set_cookie(r.headers.get_list("set-cookie"))


def test_auth_rate_limit_10_per_minute(client: TestClient) -> None:
    for _ in range(10):
        r = client.post("/api/auth/login", json={"username": "ada_1", "password": "wrong-pass"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "ada_1", "password": "wrong-pass"})
    assert r.status_code == 429
    assert r.json()["error"] == "rate_limited"
    reg = client.post("/api/auth/register", json={"username": "ada_1", "password": PASSWORD})
    assert reg.status_code == 429


def test_password_never_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    body = _register(client)
    client.post("/api/auth/login", json={"username": "ada_1", "password": PASSWORD})
    client.post("/api/auth/login", json={"username": "ada_1", "password": "wrong " + PASSWORD})
    client.post("/api/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]})
    assert PASSWORD not in caplog.text
    assert body["csrf_token"] not in caplog.text
