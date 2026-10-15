"""FastAPI app factory: health and readiness probes plus a placeholder page."""

from __future__ import annotations

from collections import Counter
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from jinja2 import Environment, FileSystemLoader

from mathtutor import __version__
from mathtutor.content.loader import LoadedContent, load_bundle, servable
from mathtutor.settings import Settings

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

TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(settings: Settings) -> FastAPI:
    # Eager: a ContentError here stops the process before it serves anything.
    content: LoadedContent = load_bundle(settings.content_path)
    templates = Jinja2Templates(
        env=Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
    )

    app = FastAPI(title=APP_NAME, version=__version__)
    app.state.settings = settings
    app.state.content = content

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

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
