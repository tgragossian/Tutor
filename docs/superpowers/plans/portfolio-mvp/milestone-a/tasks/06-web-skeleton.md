# Task 6: Web skeleton — settings, app factory, health

[Milestone A plan](../README.md) · [Spec 07](../../../../specs/2026-10-13-portfolio-core/07-application-and-web.md)

**Files:**
- Create:
  - `src/mathtutor/settings.py`
  - `src/mathtutor/web/app.py`
  - `src/mathtutor/web/templates/base.html`, `index.html`
  - `tests/integration/test_app.py`

**Interfaces:**
- Consumes: `load_bundle`, `servable`, `LoadedContent` and `ContentError` from task 4, and `__version__`.
- Produces (task 7 starts uvicorn with `mathtutor.web.app:app_factory --factory`):
  - `class Settings(BaseSettings)`, with env prefix `MATHTUTOR_`:
    - `env: Literal["development", "test", "production"] = "development"`
    - `secret_key: SecretStr | None = None`
    - `content_path: Path = Path("content/compiled/problems.json")`
  - `def create_app(settings: Settings) -> FastAPI`
  - `def app_factory() -> FastAPI`, which returns `create_app(Settings())`

**Behaviour:**
- **`Settings` validation:**
  - With `env == "production"`, `secret_key` must be set and be at least 32 characters, or a `ValidationError` is raised.
  - In development and test the key may be missing. Nothing uses it until milestone B.
- **`create_app`** loads the content **eagerly**, so a `ContentError` stops the app before it ever serves. It stores the content on `app.state.content`. No work happens at import time.
- **`GET /healthz`** → 200 `{"status": "ok", "version": __version__}`. It never touches the content.
- **`GET /readyz`:**
  - → 200 `{"status": "ready", "content_version": bundle_version, "servable": n}` when `n = len(servable(...)) > 0`
  - otherwise → 503 `{"status": "not_ready", "reason": "no_servable_problems"}`
- **`GET /`:** an HTML placeholder (Jinja, autoescape on), containing:
  - the app name and version
  - the three topic titles in order, with the number of servable problems for each
  - the OpenStax attribution sentence from the sources manifest, as a constant in `app.py`
  - It shows **no** problem answers.
- **Middleware headers on every response:**
  - `Content-Security-Policy: default-src 'self'`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: same-origin`

- [ ] **Step 1: Write the failing tests** (FastAPI `TestClient`; fixture bundles from task 4).

```python
def test_healthz(client): r = client.get("/healthz"); assert r.status_code == 200 and r.json()["status"] == "ok"
def test_readyz_ready_with_real_content(client): assert client.get("/readyz").json()["servable"] == 6
def test_readyz_503_when_nothing_servable(tmp_path):                      # review focus 5
    app = create_app(Settings(env="test", content_path=NEEDS_REVIEW_ONLY))
    assert TestClient(app).get("/readyz").status_code == 503
def test_missing_content_aborts_startup(tmp_path):
    with pytest.raises(ContentError, match="problems.json"):
        create_app(Settings(env="test", content_path=tmp_path / "problems.json"))
def test_production_requires_long_secret():                               # review focus 5
    with pytest.raises(ValidationError): Settings(env="production", secret_key="short")
def test_index_lists_topics_and_attribution(client): ...   # three titles in order, "OpenStax" present
def test_index_leaks_no_answers(client):
    body = client.get("/").text
    assert not any(p.answer.latex in body for p in REAL.bundle.problems if p.answer.kind != "choice")
def test_security_headers(client): assert "default-src 'self'" in client.get("/healthz").headers["content-security-policy"]
```

- [ ] **Step 2:** Run `uv run pytest tests/integration -q`. Expected: FAIL (`create_app` doesn't exist).
  - Make `load_bundle` raise `ContentError` with the path in the message when the file is missing, if task 4 doesn't already.
- [ ] **Step 3: Implement** `settings.py`, `app.py` and the templates as specified above.
- [ ] **Step 4:** Run `uv run pytest -q && uv run mypy src && uv run ruff check .`. Expected: PASS.
- [ ] **Step 5: Manual check.** Run `uv run uvicorn mathtutor.web.app:app_factory --factory --reload`. Expected:
  - <http://127.0.0.1:8000/> shows the three topics.
  - `/readyz` reports `"servable": 6`.
- [ ] **Step 6: Commit** with the message `feat: app factory with health/readiness and placeholder page`.
