"""App factory, health/readiness probes and the placeholder page."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from support.webapp import SpyPool, make_settings

from mathtutor import __version__
from mathtutor.content.loader import ContentError, load_bundle
from mathtutor.settings import Settings
from mathtutor.web.app import CSP, create_app

ROOT = Path(__file__).resolve().parents[2]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
GOOD_FIXTURE = ROOT / "tests" / "fixtures" / "content" / "bundles" / "good.json"
REAL = load_bundle(REAL_PATH)
TITLES = [t.title for t in sorted(REAL.bundle.topics, key=lambda t: t.order)]


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(make_settings(tmp_path), pool=SpyPool()))


@pytest.fixture
def needs_review_only(tmp_path: Path) -> Path:
    data = json.loads(GOOD_FIXTURE.read_text(encoding="utf-8"))
    for p in data["problems"]:
        p["review"] = {"status": "needs_review", "reviewer": "", "date": "", "notes": ""}
    path = tmp_path / "problems.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


def test_readyz_ready_with_real_content(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "content_version": REAL.bundle_version, "servable": 22}


def test_readyz_503_when_nothing_servable(needs_review_only: Path) -> None:
    app = create_app(Settings(env="test", content_path=needs_review_only), pool=SpyPool())
    r = TestClient(app).get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"status": "not_ready", "reason": "no_servable_problems"}


def test_missing_content_aborts_startup(tmp_path: Path) -> None:
    with pytest.raises(ContentError, match="problems.json"):
        create_app(Settings(env="test", content_path=tmp_path / "problems.json"))


def test_production_requires_long_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(env="production", secret_key="short")
    with pytest.raises(ValidationError):
        Settings(env="production")
    Settings(env="production", secret_key="x" * 32)


def test_development_allows_missing_secret() -> None:
    assert Settings(env="development").secret_key is None


def test_settings_read_env_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MATHTUTOR_ENV", "test")
    monkeypatch.setenv("MATHTUTOR_CONTENT_PATH", "elsewhere.json")
    s = Settings()
    assert s.env == "test" and s.content_path == Path("elsewhere.json")


def test_pool_settings_default_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (Settings().pool_size, Settings().pool_memory_mb) == (1, 384)
    monkeypatch.setenv("MATHTUTOR_POOL_SIZE", "2")
    monkeypatch.setenv("MATHTUTOR_POOL_MEMORY_MB", "256")
    assert (Settings().pool_size, Settings().pool_memory_mb) == (2, 256)


def test_pool_settings_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Settings(pool_size=0)
    with pytest.raises(ValidationError):
        Settings(pool_memory_mb=0)


def test_create_app_passes_pool_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_pool(**kwargs: object) -> SpyPool:
        seen.update(kwargs)
        return SpyPool()

    monkeypatch.setattr("mathtutor.web.app.VerifierPool", fake_pool)
    settings = make_settings(tmp_path).model_copy(
        update={"pool_size": 2, "pool_memory_mb": 256, "help_generator": "off"}
    )
    with TestClient(create_app(settings)):
        pass
    assert seen == {"size": 2, "memory_mb": 256}


def _recording_pools(monkeypatch: pytest.MonkeyPatch) -> list[tuple[dict[str, object], SpyPool]]:
    made: list[tuple[dict[str, object], SpyPool]] = []

    def fake_pool(**kwargs: object) -> SpyPool:
        made.append((kwargs, SpyPool()))
        return made[-1][1]

    monkeypatch.setattr("mathtutor.web.app.VerifierPool", fake_pool)
    return made


def test_guard_pool_started_and_closed_when_help_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = _recording_pools(monkeypatch)
    settings = make_settings(tmp_path).model_copy(update={"guard_pool_memory_mb": 200})
    app = create_app(settings)
    with TestClient(app) as c:
        assert c.get("/readyz").status_code == 200
        assert len(made) == 2
        (_, grading), (guard_kwargs, guard) = made
        assert app.state.pool is grading and app.state.guard_pool is guard
    assert guard_kwargs == {
        "size": 1,
        "deadline_s": 2.0,
        "queue_max": 4,
        "queue_wait_s": 1.0,
        "memory_mb": 200,
    }
    assert grading.closed and guard.closed


def test_guard_pool_not_started_when_help_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = _recording_pools(monkeypatch)
    settings = make_settings(tmp_path).model_copy(update={"help_generator": "off"})
    app = create_app(settings)
    with TestClient(app) as c:
        assert c.get("/readyz").status_code == 200
        assert len(made) == 1
        assert app.state.guard_pool is None


def test_injected_pools_are_used_as_is(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    made = _recording_pools(monkeypatch)
    pool, guard = SpyPool(), SpyPool()
    app = create_app(make_settings(tmp_path), pool=pool, guard_pool=guard)
    with TestClient(app):
        assert app.state.guard_pool is guard
    assert made == [] and not guard.closed and not pool.closed
    only_pool = create_app(make_settings(tmp_path), pool=SpyPool())
    with TestClient(only_pool):
        assert only_pool.state.guard_pool is None
    assert made == []


def test_injected_guard_pool_with_owned_grading_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    made = _recording_pools(monkeypatch)
    guard = SpyPool()
    app = create_app(make_settings(tmp_path), guard_pool=guard)
    with TestClient(app):
        assert len(made) == 1  # the grading pool only
        assert app.state.guard_pool is guard
    assert made[0][1].closed and not guard.closed


def test_readyz_ignores_guard_pool(tmp_path: Path) -> None:
    guard = SpyPool()
    guard.is_alive = False
    app = create_app(make_settings(tmp_path), pool=SpyPool(), guard_pool=guard)
    assert TestClient(app).get("/readyz").status_code == 200


def test_index_lists_topics_and_attribution(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    body = r.text
    positions = [body.index(t) for t in TITLES]
    assert positions == sorted(positions)
    assert "OpenStax" in body and "CC BY-NC-SA 4.0" in body
    assert __version__ in body


def test_index_leaks_no_answers(client: TestClient) -> None:
    body = client.get("/").text
    # Ruling R5: only answers long enough not to appear innocently ("2", "x").
    answers = [p.answer.latex for p in REAL.bundle.problems if p.answer.kind != "choice"]
    assert not any(a in body for a in answers if len(a) >= 4)


def test_security_headers(client: TestClient) -> None:
    for path in ("/healthz", "/readyz", "/"):
        h = client.get(path).headers
        assert h["content-security-policy"] == CSP
        assert h["x-content-type-options"] == "nosniff"
        assert h["referrer-policy"] == "same-origin"


def test_security_headers_on_500() -> None:
    app = create_app(Settings(env="test", content_path=REAL_PATH))

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("boom")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500
    assert r.headers["content-security-policy"] == CSP
    assert r.headers["x-content-type-options"] == "nosniff"
