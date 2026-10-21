"""Session cookies, the CSRF check and in-memory rate limits (spec 07).

Rate limits live in process memory, so they assume a single app process (one uvicorn worker).
"""

from __future__ import annotations

import hmac
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from mathtutor.application.auth import SESSION_LIFETIME, AuthService, LoginResult
from mathtutor.application.errors import Forbidden, RateLimited, Unauthorized

COOKIE_NAME = "mt_session"
CSRF_HEADER = "X-CSRF-Token"
CSRF_FIELD = "csrf_token"
_SALT = "mt_session"


@dataclass(frozen=True)
class AuthContext:
    user_id: int
    csrf_token: str
    token: str


class CookieCodec:
    """Signs the session token into the cookie value; ``Secure`` everywhere but development."""

    def __init__(self, secret: str, secure: bool) -> None:
        self._serializer = URLSafeSerializer(secret, salt=_SALT)
        self.secure = secure

    def set(self, response: Response, login: LoginResult) -> None:
        response.set_cookie(
            COOKIE_NAME,
            self._serializer.dumps(login.token),
            max_age=int(SESSION_LIFETIME.total_seconds()),
            path="/",
            httponly=True,
            secure=self.secure,
            samesite="lax",
        )

    def clear(self, response: Response) -> None:
        response.delete_cookie(
            COOKIE_NAME, path="/", httponly=True, secure=self.secure, samesite="lax"
        )

    def token(self, request: Request) -> str | None:
        raw = request.cookies.get(COOKIE_NAME)
        if not raw:
            return None
        try:
            value = self._serializer.loads(raw)
        except BadSignature:
            return None
        return value if isinstance(value, str) else None


def current_user(request: Request) -> AuthContext:
    """FastAPI dependency: the signed-in user, or ``Unauthorized``."""
    codec: CookieCodec = request.app.state.cookies
    auth: AuthService = request.app.state.auth
    token = codec.token(request)
    resolved = auth.resolve(token) if token else None
    if token is None or resolved is None:
        raise Unauthorized("Please sign in.")
    user_id, csrf_token = resolved
    return AuthContext(user_id=user_id, csrf_token=csrf_token, token=token)


async def require_csrf(
    request: Request, auth: Annotated[AuthContext, Depends(current_user)]
) -> AuthContext:
    """Every cookie-authenticated POST carries the session's CSRF token (header or form field)."""
    sent = request.headers.get(CSRF_HEADER)
    if sent is None and request.headers.get("content-type", "").startswith(
        ("application/x-www-form-urlencoded", "multipart/form-data")
    ):
        field = (await request.form()).get(CSRF_FIELD)
        sent = field if isinstance(field, str) else None
    if sent is None or not hmac.compare_digest(sent.encode(), auth.csrf_token.encode()):
        raise Forbidden("Missing or invalid CSRF token.", code="csrf_failed")
    return auth


CurrentUser = Annotated[AuthContext, Depends(current_user)]
CsrfUser = Annotated[AuthContext, Depends(require_csrf)]


class RateLimiter:
    """Sliding window per key, in process memory. Rejected hits are not recorded."""

    def __init__(
        self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window = window_s
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                raise RateLimited("Too many requests. Please wait a minute and try again.")
            hits.append(now)
            if len(self._hits) > 10_000:
                self._prune(now)

    def _prune(self, now: float) -> None:
        stale = [k for k, h in self._hits.items() if not h or h[-1] <= now - self._window]
        for key in stale:
            del self._hits[key]


def client_ip(request: Request) -> str:
    """The peer address; uvicorn's ``--proxy-headers`` makes this the client behind Caddy."""
    return request.client.host if request.client else "unknown"
