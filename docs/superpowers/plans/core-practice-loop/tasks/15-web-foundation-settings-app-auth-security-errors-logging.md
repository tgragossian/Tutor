[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 739–779. Review findings remain unresolved.

### Task 15: Web foundation — settings, app, auth, security, errors, logging

**Files:**
- Create: `src/mathtutor/web/__init__.py`, `settings.py`, `app.py`, `auth.py`, `security.py`, `errors.py`, `logging.py`, `tests/web/conftest.py`, `tests/web/test_auth.py`, `tests/web/test_security.py`

**Interfaces:**
- Produces:
  - `class Settings(BaseSettings)` with:
    - `secret_key: str`
    - `database_url: str = "sqlite:///./data/mathtutor.db"`
    - `content_dir: Path = Path("content")`
    - `secure_cookies: bool = True`
    - `verifier_timeout_s: float = 3.0`
    - `verifier_workers: int = 2`
  - `def create_app(settings: Settings) -> FastAPI`. Startup does `load_content`, engine and sessionmaker, `VerifierPool`; these are stored on `app.state`. Shutdown closes the pool.
  - **Auth:** Starlette `SessionMiddleware` with a signed cookie, `https_only=settings.secure_cookies`, `same_site="lax"`.
    - `hash_password`, `verify_password` (argon2)
    - dependency `current_user(request, db) -> User`, which raises a 401 `ApiError`
    - routes `POST /api/auth/register|login|logout`, enforcing the username and password rules from Global Constraints
  - **CSRF:** the token lives in the session; every non-GET request must send header `X-CSRF-Token` or form field `csrf_token`. `GET /api/auth/csrf` returns it.
  - **Rate limiting:** `class RateLimiter(limit: int, window_s: float)`, an in-memory sliding window with `hit(key) -> bool`. Exceeding it raises a 429 `ApiError`.
  - **Errors:** `class ApiError(Exception): status: int; code: str; message: str`. Handlers render `{error, message}`; pydantic validation errors become 422 with `error="validation"`.
  - **Logging:** structlog JSON with a `request_id` middleware.
  - `GET /healthz` returns `{status: "ok"}`.

- [ ] **Step 1: Write the failing tests:**
  - register → login → logout works
  - a bad username or short password → 422
  - a duplicate username → 409 `username_taken`
  - a wrong password → 401
  - a POST without a CSRF token → 403
  - the 11th login within a minute → 429
  - `/healthz` → 200
  - the password does not appear in captured logs
- [ ] **Step 2:** Run `uv run pytest tests/web -v`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(web): app factory, auth, CSRF, rate limits, errors, logging`.

---

<!-- End preserved source. -->
