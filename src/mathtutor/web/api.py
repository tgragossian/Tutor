"""JSON routes. Each one calls an application service; none holds session rules."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from mathtutor.application.auth import AuthService
from mathtutor.application.errors import Unauthorized
from mathtutor.web.schemas import AuthUser, Credentials
from mathtutor.web.security import CookieCodec, CsrfUser, CurrentUser, RateLimiter, client_ip

auth_router = APIRouter(prefix="/api/auth")


def _auth(request: Request) -> AuthService:
    service: AuthService = request.app.state.auth
    return service


def _cookies(request: Request) -> CookieCodec:
    codec: CookieCodec = request.app.state.cookies
    return codec


def _limit_auth(request: Request) -> None:
    limiter: RateLimiter = request.app.state.auth_limiter
    limiter.hit(client_ip(request))


@auth_router.post("/register")
def register(body: Credentials, request: Request, response: Response) -> AuthUser:
    _limit_auth(request)
    result = _auth(request).register(body.username, body.password)
    _drop_previous_session(request)
    _cookies(request).set(response, result)
    return AuthUser(username=_username(request, result.user_id), csrf_token=result.csrf_token)


@auth_router.post("/login")
def login(body: Credentials, request: Request, response: Response) -> AuthUser:
    _limit_auth(request)
    result = _auth(request).login(body.username, body.password)
    _drop_previous_session(request)
    _cookies(request).set(response, result)
    return AuthUser(username=_username(request, result.user_id), csrf_token=result.csrf_token)


@auth_router.post("/logout")
def logout(auth: CsrfUser, request: Request, response: Response) -> dict[str, bool]:
    _auth(request).logout(auth.token)
    _cookies(request).clear(response)
    return {"ok": True}


@auth_router.get("/me")
def me(auth: CurrentUser, request: Request) -> AuthUser:
    return AuthUser(username=_username(request, auth.user_id), csrf_token=auth.csrf_token)


def _drop_previous_session(request: Request) -> None:
    """Session rotation: the cookie's old server-side row is deleted on login."""
    old = _cookies(request).token(request)
    if old is not None:
        _auth(request).logout(old)


def _username(request: Request, user_id: int) -> str:
    name = _auth(request).username(user_id)
    if name is None:
        raise Unauthorized("Please sign in.")
    return name
