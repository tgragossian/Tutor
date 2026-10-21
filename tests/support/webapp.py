"""A test app with a real SQLite file and a scripted spy pool, plus a logged-in client."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.settings import Settings
from mathtutor.store.db import upgrade
from mathtutor.verify.types import CheckRequest, CheckResult, FormatIssue, Verdict, VerifierBusy
from mathtutor.web.app import create_app

ROOT = Path(__file__).resolve().parents[2]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
SECRET = "s" * 40
PASSWORD = "correct horse battery"

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
INCORRECT = Verdict(VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION)
UNABLE = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.NOT_PROVEN, Method.NONE)


class SpyPool:
    """Records every request. Returns scripted outcomes, else ``default``."""

    def __init__(self) -> None:
        self.requests: list[CheckRequest] = []
        self.script: list[Verdict | FormatIssue | type[VerifierBusy]] = []
        self.default: Verdict | FormatIssue = UNABLE
        self.is_alive = True
        self.closed = False

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        outcome = self.script.pop(0) if self.script else self.default
        if outcome is VerifierBusy:
            raise VerifierBusy("full")
        assert isinstance(outcome, Verdict | FormatIssue)
        return CheckResult(outcome, "0.1.0+test", worker_ms=5, queue_ms=1)

    def alive(self) -> bool:
        return self.is_alive

    def close(self) -> None:
        self.closed = True


def make_settings(tmp_path: Path, env: str = "test") -> Settings:
    url = f"sqlite:///{(tmp_path / 'web.db').as_posix()}"
    upgrade(url)
    return Settings(env=env, content_path=REAL_PATH, database_url=url, secret_key=SECRET)  # type: ignore[arg-type]


def make_client(tmp_path: Path, pool: SpyPool) -> TestClient:
    app = create_app(make_settings(tmp_path), pool=pool)
    return TestClient(app, base_url="https://testserver")


def login(client: TestClient, username: str = "ada_1") -> str:
    """Register and return the CSRF token; also sets it as a default header."""
    r = client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    csrf: str = r.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return csrf


def start(client: TestClient, topics: list[str] | None = None) -> int:
    r = client.post("/api/sessions", json={"topics": topics or ["derivatives.basic_rules"]})
    assert r.status_code == 201, r.text
    session_id: int = r.json()["session_id"]
    return session_id


SubmitFn = Callable[..., object]
