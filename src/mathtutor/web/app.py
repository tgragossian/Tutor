"""FastAPI app factory: services, routes, error handlers and health/readiness probes."""

from __future__ import annotations

import secrets
from collections import Counter
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mathtutor import __version__
from mathtutor.application.auth import AuthService
from mathtutor.application.errors import AppError
from mathtutor.content.loader import LoadedContent, load_bundle, servable
from mathtutor.settings import Settings
from mathtutor.store.db import make_engine, make_sessionmaker
from mathtutor.web.api import auth_router
from mathtutor.web.security import CookieCodec, RateLimiter

APP_NAME = "Calculus Tutor"

# Mirrors "Attribution shown in the UI" in content/sources/openstax-calculus-v1.md.
ATTRIBUTION = (
    'Problems from Calculus Volume 1 by Gilbert Strang and Edwin "Jed" Herman, OpenStax, '
    "licensed under CC BY-NC-SA 4.0. Access for free at "
    "https://openstax.org/books/calculus-volume-1/pages/1-introduction"
)

SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
}


class _SecureFastAPI(FastAPI):
    """Wraps the whole stack, including Starlette's 500 handler, which sits outside
    anything added with ``add_middleware``."""

    def build_middleware_stack(self) -> ASGIApp:
        return SecurityHeadersMiddleware(super().build_middleware_stack())


class SecurityHeadersMiddleware:
    """Pure ASGI: adds headers at ``http.response.start`` so error responses get them too."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [
                    (k, v)
                    for k, v in message.get("headers", [])
                    if k.decode("latin-1").lower() not in {h.lower() for h in SECURITY_HEADERS}
                ]
                headers += [(k.lower().encode(), v.encode()) for k, v in SECURITY_HEADERS.items()]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


TEMPLATES_DIR = Path(__file__).parent / "templates"

AUTH_LIMIT = (10, 60.0)  # per client IP
SUBMIT_LIMIT = (30, 60.0)  # per user


def _utcnow() -> datetime:
    return datetime.now(UTC)


def create_app(settings: Settings) -> FastAPI:
    # Eager: a ContentError here stops the process before it serves anything.
    content: LoadedContent = load_bundle(settings.content_path)
    templates = Jinja2Templates(
        env=Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    )

    engine = make_engine(settings.database_url)
    # Production requires a secret (Settings validator); elsewhere a per-process one is enough.
    secret = (
        settings.secret_key.get_secret_value() if settings.secret_key else secrets.token_hex(32)
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    app = _SecureFastAPI(title=APP_NAME, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.content = content
    app.state.engine = engine
    app.state.sessions = make_sessionmaker(engine)
    app.state.auth = AuthService(app.state.sessions, _utcnow)
    app.state.cookies = CookieCodec(secret, secure=settings.env != "development")
    app.state.auth_limiter = RateLimiter(*AUTH_LIMIT)
    app.state.submit_limiter = RateLimiter(*SUBMIT_LIMIT)

    @app.exception_handler(AppError)
    async def app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse({"error": exc.code, "message": exc.message}, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()})
        message = "Invalid request" + (f": {', '.join(fields)}" if fields else "") + "."
        return JSONResponse({"error": "invalid_request", "message": message}, status_code=422)

    app.include_router(auth_router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        n = len(servable(content))
        if n == 0:
            return JSONResponse(
                {"status": "not_ready", "reason": "no_servable_problems"}, status_code=503
            )
        return JSONResponse(
            {"status": "ready", "content_version": content.bundle_version, "servable": n}
        )

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        counts = Counter(p.topic for p in servable(content))
        topics = [
            {"title": t.title, "section": t.section, "servable": counts[t.topic_id]}
            for t in sorted(content.bundle.topics, key=lambda t: t.order)
        ]
        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "app_name": APP_NAME,
                "version": __version__,
                "topics": topics,
                "attribution": ATTRIBUTION,
            },
        )

    return app


def app_factory() -> FastAPI:
    return create_app(Settings())
