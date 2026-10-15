# Task 11: Accounts, cookie sessions, CSRF, rate limits

[Milestone B plan](../README.md) · [Spec 07](../../../../specs/2026-10-13-portfolio-core/07-application-and-web.md) · Ruling R2

**Files:**
- Create: `src/mathtutor/application/__init__.py`, `errors.py`, `auth.py`
- Create: `src/mathtutor/web/security.py`
- Create: `tests/unit/application/test_auth.py`, `tests/integration/test_auth_routes.py`
- Modify: `pyproject.toml` (`uv add argon2-cffi itsdangerous`), `src/mathtutor/web/app.py`, `web/schemas.py`

**Interfaces:**
- Consumes: `make_sessionmaker`, `User`, `WebSession` (task 10); `Settings.secret_key`, `Settings.env`.
- Produces (`application/errors.py`): `class AppError(Exception)` with subclasses `Unauthorized` (401), `Forbidden` (403), `NotFound` (404), `StaleItem` (409), `InvalidAction` (409), `Conflict` (409, e.g. username taken), `RateLimited` (429), `Busy` (503). Each has `code: str` used as the JSON `error`.
- Produces (`application/auth.py`):
  - `@dataclass(frozen=True) class LoginResult: user_id: int; token: str; csrf_token: str; expires_at: datetime`
  - `class AuthService: __init__(self, sessions: sessionmaker[Session], clock: Callable[[], datetime])`
    - `register(username: str, password: str) -> LoginResult` — username `^[a-z0-9_]{3,32}$`, password 8–128 chars (`InvalidAction` otherwise), argon2 hash; logs the user in.
    - `login(username: str, password: str) -> LoginResult` — same error for unknown user and wrong password (`Unauthorized`); creates a new `web_sessions` row (rotation: the old cookie's row, if any, is deleted by the route).
    - `resolve(token: str) -> tuple[int, str] | None` — `(user_id, csrf_token)` for an unexpired session.
    - `logout(token: str) -> None` — deletes the row.
  - Tokens: `secrets.token_urlsafe(32)`; stored as SHA-256 hex; lifetime 14 days.
- Produces (`web/security.py`):
  - Cookie `mt_session`: value = `itsdangerous.URLSafeSerializer(secret).dumps(token)`; `HttpOnly`, `SameSite=Lax`, `Secure` unless `env == "development"`, `Max-Age` 14 days.
  - `def current_user(request) -> AuthContext` (FastAPI dependency; `AuthContext(user_id, csrf_token, token)`); raises `Unauthorized`.
  - `def require_csrf(request, auth)` — every cookie-authenticated POST must carry header `X-CSRF-Token` or form field `csrf_token` equal to the session's token (`hmac.compare_digest`), else 403.
  - `class RateLimiter: def __init__(self, limit: int, window_s: float, clock)`; `def hit(self, key: str) -> None` raises `RateLimited`. Sliding window, in memory, per process (documented single-process assumption).
- Produces (JSON routes): `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` → `{username, csrf_token}`.

- [ ] **Step 1: Write the failing tests.**

```python
def test_register_then_login(auth): r = auth.register("ada_1", "correct horse"); assert auth.resolve(r.token)[0] == r.user_id
def test_bad_username_and_password_lengths(auth): ...        # "AB", 33 chars, 7-char and 129-char passwords → InvalidAction
def test_duplicate_username_conflict(auth): ...
def test_wrong_password_same_error_as_unknown_user(auth): ...
def test_expired_session_does_not_resolve(auth, clock): ...   # advance clock 14 days + 1 s
def test_login_rotates_session(client): ...                   # cookie value changes; old token no longer resolves
def test_logout_clears_server_side(client): ...               # replaying the old cookie → 401
def test_post_without_csrf_is_403(client): ...                # logged-in POST /api/auth/logout without header
def test_cookie_flags(client): ...                            # HttpOnly; SameSite=lax; Secure when env=production
def test_auth_rate_limit_10_per_minute(client): ...           # 11th login attempt from one IP within 60 s → 429
def test_password_never_logged(client, caplog): ...
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/application tests/integration/test_auth_routes.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the service, the security helpers, the routes, and an `AppError` exception handler in `create_app` that returns `{error, message}` with the class's status. Build `AuthService` and the two `RateLimiter`s (auth 10/60 s per client IP, submit 30/60 s per user) in `create_app`; store on `app.state`.
- [ ] **Step 4:** Run `uv run pytest -q && uv run mypy src`. Expected: PASS.
- [ ] **Step 5: Commit** `feat: accounts, server-side cookie sessions, CSRF and rate limits`.
