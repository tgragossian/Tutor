"""FastAPI app factory: services, routes, error handlers and health/readiness probes."""

from __future__ import annotations

import json
import logging
import secrets
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mathtutor import __version__
from mathtutor.application.auth import AuthService
from mathtutor.application.errors import AppError, DatabaseBusy
from mathtutor.application.practice import Pool, PracticeService
from mathtutor.content.loader import LoadedContent, load_bundle, servable
from mathtutor.help.config import HelpConfig, load_help_config
from mathtutor.help.context import Confusion, load_confusions
from mathtutor.help.generator import ClaudeGenerator, Generator, ScriptedGenerator
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.help.ledger import Ledger
from mathtutor.help.pipeline import HelpPipeline
from mathtutor.help.service import HelpService
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import Corpus, CorpusError, load_corpus
from mathtutor.settings import Settings
from mathtutor.store.db import is_lock_error, make_engine, make_sessionmaker
from mathtutor.verify.pool import VerifierPool
from mathtutor.web.api import auth_router, help_router, practice_router
from mathtutor.web.logging import BodyLimitMiddleware, RequestLogMiddleware
from mathtutor.web.pages import APP_NAME, pages_router, render_error
from mathtutor.web.security import CookieCodec, RateLimiter

# R4: start from default-src 'self'; see docs/ops/security.md for every addition.
CSP = "default-src 'self'; style-src-attr 'unsafe-inline'"

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
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
STATIC_DIR = Path(__file__).parent / "static"

AUTH_LIMIT = (10, 60.0)  # per client IP
SUBMIT_LIMIT = (30, 60.0)  # per user


logger = logging.getLogger(__name__)

HTTP_CODES = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _wants_html(request: Request) -> bool:
    """Page routes get an HTML error page; the API and static files keep JSON."""
    path = request.url.path
    return not path.startswith(("/api/", "/static/", "/healthz", "/readyz"))


def _vendor_tags(manifest_path: Path) -> dict[str, list[dict[str, str]]]:
    """Script and modulepreload tags with SRI hashes, read once from tools/vendor.mjs output."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    integrity: dict[str, str] = manifest["integrity"]
    entries: list[str] = manifest["entries"]
    return {
        "scripts": [{"src": f"/static/vendor/{p}", "integrity": integrity[p]} for p in entries],
        "preloads": [
            {"href": f"/static/vendor/{p}", "integrity": h}
            for p, h in sorted(integrity.items())
            if p not in entries
        ],
    }


def _database_ok(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


class _Pool(Pool, Protocol):
    def alive(self) -> bool: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class _HelpParts:
    """What enabled help needs, loaded once at startup: the index is never rebuilt per request."""

    corpus: Corpus
    index: Bm25Index
    confusions: dict[str, list[Confusion]]
    generator: Generator


def _help_wanted(settings: Settings) -> bool:
    if settings.help_generator == "off":
        return False
    if settings.help_generator == "claude":
        key = settings.anthropic_api_key
        return key is not None and bool(key.get_secret_value())
    return True


def _load_help(
    settings: Settings, cfg: HelpConfig, generator: Generator | None
) -> _HelpParts | None:
    """Help is enabled only when it is not off, a ``claude`` generator has a key, and the corpus
    loads with a valid hash. Otherwise None: items carry ``help: null``, ``/api/help`` answers
    ``unavailable``, and the app still starts and stays ready. Logs the error type only."""
    if not _help_wanted(settings):
        return None
    try:
        corpus = load_corpus(settings.corpus_path)
        confusions = load_confusions(settings.confusions_path)
    except (CorpusError, OSError, ValueError) as exc:
        logger.warning("help disabled: %s", type(exc).__name__)
        return None
    if generator is None:
        if settings.help_generator == "scripted":
            generator = ScriptedGenerator([])
        else:
            assert settings.anthropic_api_key is not None  # _help_wanted checked it
            generator = ClaudeGenerator(settings.anthropic_api_key.get_secret_value())
    return _HelpParts(corpus, Bm25Index.build(corpus, cfg.retrieval), confusions, generator)


def _help_service(
    sessions: sessionmaker[Session],
    cfg: HelpConfig,
    parts: _HelpParts | None,
    grading: Pool,
    guard: Pool | None,
) -> HelpService:
    """The help service. Without ``parts`` or a guard pool it is disabled and never touches a
    corpus, generator or guard: help text that cannot be checked is never served."""
    ledger = Ledger(sessions, cfg, _utcnow)
    if parts is None or guard is None:
        empty = Corpus({}, "", "none")
        pipeline = HelpPipeline(
            cfg,
            empty,
            Bm25Index.build(empty, cfg.retrieval),
            ScriptedGenerator([]),
            LeakGuard(grading, cfg.guard, time.monotonic),
            time.monotonic,
        )
        return HelpService(sessions, cfg, ledger, pipeline, grading, {}, now=_utcnow, enabled=False)
    pipeline = HelpPipeline(
        cfg,
        parts.corpus,
        parts.index,
        parts.generator,
        LeakGuard(guard, cfg.guard, time.monotonic),
        time.monotonic,
    )
    return HelpService(sessions, cfg, ledger, pipeline, grading, parts.confusions, now=_utcnow)


def create_app(
    settings: Settings,
    *,
    pool: _Pool | None = None,
    guard_pool: _Pool | None = None,
    generator: Generator | None = None,
) -> FastAPI:
    """Build the app. Without ``pool``, a ``VerifierPool`` is started when the app starts
    (lifespan) and closed when it stops; an injected pool belongs to the caller.

    The leak guard's pool (``app.state.guard_pool``) is started alongside it only when the app
    starts its own grading pool, help is enabled (``_load_help``) and no ``guard_pool`` is
    injected; an injected one is used as is and never closed by the app. ``generator``
    replaces the one ``settings.help_generator`` selects (tests).
    """
    # Eager: a ContentError here stops the process before it serves anything.
    content: LoadedContent = load_bundle(settings.content_path)
    templates = Jinja2Templates(
        env=Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    )
    vendor = _vendor_tags(STATIC_DIR / "vendor" / "manifest.json")
    help_cfg = load_help_config(settings.help_config_path)
    help_parts = _load_help(settings, help_cfg, generator)

    engine = make_engine(settings.database_url)
    sessions = make_sessionmaker(engine)
    # Production requires a secret (Settings validator); elsewhere a per-process one is enough.
    secret = (
        settings.secret_key.get_secret_value() if settings.secret_key else secrets.token_hex(32)
    )

    def attach_pool(p: _Pool) -> None:
        app.state.pool = p
        app.state.practice = PracticeService(sessions, content, p, _utcnow)
        app.state.help = _help_service(sessions, help_cfg, help_parts, p, app.state.guard_pool)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        owned: list[_Pool] = []
        try:
            if pool is None:
                # check_fn=None: the worker imports the checker, never this process (R8).
                grading = await run_in_threadpool(
                    lambda: VerifierPool(size=settings.pool_size, memory_mb=settings.pool_memory_mb)
                )
                owned.append(grading)
                if guard_pool is None and help_parts is not None:
                    # The leak guard's own worker, so help checks never queue behind grading.
                    guard = await run_in_threadpool(
                        lambda: VerifierPool(
                            size=1,
                            deadline_s=2.0,
                            queue_max=4,
                            queue_wait_s=1.0,
                            memory_mb=settings.guard_pool_memory_mb,
                        )
                    )
                    owned.append(guard)
                    app.state.guard_pool = guard
                attach_pool(grading)  # after the guard pool: help is built with it
            yield
        finally:
            for p in owned:
                await run_in_threadpool(p.close)
            engine.dispose()

    app = _SecureFastAPI(title=APP_NAME, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.content = content
    app.state.engine = engine
    app.state.sessions = sessions
    app.state.pool = None
    app.state.guard_pool = guard_pool
    app.state.help = None
    app.state.help_generator = None if help_parts is None else help_parts.generator
    app.state.templates = templates
    app.state.vendor = vendor
    app.state.auth = AuthService(sessions, _utcnow)
    app.state.cookies = CookieCodec(secret, secure=settings.env != "development")
    app.state.auth_limiter = RateLimiter(*AUTH_LIMIT)
    app.state.submit_limiter = RateLimiter(*SUBMIT_LIMIT)
    if pool is not None:
        attach_pool(pool)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(RequestLogMiddleware)

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> Response:
        headers = {"Retry-After": str(exc.retry_after_s)} if exc.retry_after_s else None
        if _wants_html(request):
            return render_error(request, exc.status, exc.message)
        return JSONResponse(
            {"error": exc.code, "message": exc.message}, status_code=exc.status, headers=headers
        )

    @app.exception_handler(OperationalError)
    async def database_error(request: Request, exc: OperationalError) -> Response:
        """Any lock that outlasts busy_timeout, on any route, is a retryable 503."""
        if not is_lock_error(exc):
            raise exc
        return await app_error(request, DatabaseBusy("The database is busy. Please try again."))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        if _wants_html(request):
            return render_error(request, exc.status_code, str(exc.detail))
        code = HTTP_CODES.get(exc.status_code, "http_error")
        return JSONResponse(
            {"error": code, "message": str(exc.detail)},
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = sorted({".".join(str(p) for p in e["loc"][1:]) for e in exc.errors()})
        message = "Invalid request" + (f": {', '.join(fields)}" if fields else "") + "."
        return JSONResponse({"error": "invalid_request", "message": message}, status_code=422)

    app.include_router(auth_router)
    app.include_router(practice_router)
    app.include_router(help_router)
    app.include_router(pages_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        n = len(servable(content))
        reason = None
        if n == 0:
            reason = "no_servable_problems"
        elif not _database_ok(engine):
            reason = "database_unavailable"
        elif app.state.pool is None or not app.state.pool.alive():
            reason = "verifier_pool_down"
        if reason is not None:
            return JSONResponse({"status": "not_ready", "reason": reason}, status_code=503)
        return JSONResponse(
            {"status": "ready", "content_version": content.bundle_version, "servable": n}
        )

    return app


def app_factory() -> FastAPI:
    return create_app(Settings())
