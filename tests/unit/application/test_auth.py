from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from mathtutor.application.auth import SESSION_LIFETIME, AuthService
from mathtutor.application.errors import Conflict, InvalidAction, RateLimited, Unauthorized
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade
from mathtutor.web.security import RateLimiter


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def auth(tmp_path: Path, clock: Clock) -> Iterator[AuthService]:
    url = f"sqlite:///{(tmp_path / 'auth.db').as_posix()}"
    upgrade(url)
    engine = make_engine(url)
    yield AuthService(make_sessionmaker(engine), clock)
    engine.dispose()


def test_register_then_login(auth: AuthService) -> None:
    r = auth.register("ada_1", "correct horse")
    resolved = auth.resolve(r.token)
    assert resolved is not None
    assert resolved[0] == r.user_id
    assert resolved[1] == r.csrf_token
    again = auth.login("ada_1", "correct horse")
    assert again.user_id == r.user_id
    assert again.token != r.token


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("AB", "correct horse"),
        ("a" * 33, "correct horse"),
        ("has space", "correct horse"),
        ("ada", "x" * 7),
        ("ada", "x" * 129),
    ],
)
def test_bad_username_and_password_lengths(auth: AuthService, username: str, password: str) -> None:
    with pytest.raises(InvalidAction):
        auth.register(username, password)


def test_boundary_lengths_accepted(auth: AuthService) -> None:
    auth.register("abc", "x" * 8)
    auth.register("b" * 32, "x" * 128)


def test_username_is_case_folded(auth: AuthService) -> None:
    r = auth.register("Ada_1", "correct horse")
    assert auth.login("ada_1", "correct horse").user_id == r.user_id


def test_duplicate_username_conflict(auth: AuthService) -> None:
    auth.register("ada_1", "correct horse")
    with pytest.raises(Conflict):
        auth.register("ada_1", "another password")


def test_wrong_password_same_error_as_unknown_user(auth: AuthService) -> None:
    auth.register("ada_1", "correct horse")
    with pytest.raises(Unauthorized) as wrong:
        auth.login("ada_1", "wrong horse")
    with pytest.raises(Unauthorized) as unknown:
        auth.login("nobody", "wrong horse")
    assert (wrong.value.code, str(wrong.value)) == (unknown.value.code, str(unknown.value))


def test_expired_session_does_not_resolve(auth: AuthService, clock: Clock) -> None:
    r = auth.register("ada_1", "correct horse")
    clock.now += SESSION_LIFETIME
    assert auth.resolve(r.token) is not None
    clock.now += timedelta(seconds=1)
    assert auth.resolve(r.token) is None
    assert SESSION_LIFETIME == timedelta(days=14)


def test_logout_deletes_session(auth: AuthService) -> None:
    r = auth.register("ada_1", "correct horse")
    auth.logout(r.token)
    assert auth.resolve(r.token) is None
    auth.logout(r.token)  # idempotent


def test_unknown_token_does_not_resolve(auth: AuthService) -> None:
    assert auth.resolve("not-a-token") is None


def test_rate_limiter_sliding_window() -> None:
    t = [0.0]
    limiter = RateLimiter(limit=3, window_s=60, clock=lambda: t[0])
    for _ in range(3):
        limiter.hit("ip")
    with pytest.raises(RateLimited):
        limiter.hit("ip")
    limiter.hit("other")
    t[0] = 59.9
    with pytest.raises(RateLimited):
        limiter.hit("ip")
    t[0] = 60.1
    limiter.hit("ip")
