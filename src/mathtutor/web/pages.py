"""HTML routes. Forms post here; the practice page itself talks to the JSON API."""

from __future__ import annotations

from collections import Counter
from typing import Annotated, Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from mathtutor import __version__
from mathtutor.application.errors import AppError, Unauthorized
from mathtutor.content.loader import LoadedContent, servable
from mathtutor.web.api import (
    auth_service,
    cookie_codec,
    drop_previous_session,
    limit_auth,
    practice_service,
)
from mathtutor.web.security import AuthContext, CsrfUser, current_user

pages_router = APIRouter()

APP_NAME = "Calculus Tutor"

# Mirrors "Attribution shown in the UI" in content/sources/openstax-calculus-v1.md.
ATTRIBUTION = (
    'Problems from Calculus Volume 1 by Gilbert Strang and Edwin "Jed" Herman, OpenStax, '
    "licensed under CC BY-NC-SA 4.0. Access for free at "
    "https://openstax.org/books/calculus-volume-1/pages/1-introduction"
)

FormText = Annotated[str, Form(max_length=256)]


def optional_user(request: Request) -> AuthContext | None:
    try:
        return current_user(request)
    except Unauthorized:
        return None


def render(
    request: Request, name: str, context: dict[str, Any] | None = None, status: int = 200
) -> HTMLResponse:
    user = optional_user(request)
    base = {
        "app_name": APP_NAME,
        "version": __version__,
        "attribution": ATTRIBUTION,
        "username": auth_service(request).username(user.user_id) if user else None,
        "csrf_token": user.csrf_token if user else None,
        "vendor": request.app.state.vendor,
    }
    response: HTMLResponse = request.app.state.templates.TemplateResponse(
        request, name, {**base, **(context or {})}, status_code=status
    )
    return response


def render_error(request: Request, status: int, message: str) -> HTMLResponse:
    return render(request, "error.html", {"status": status, "message": message}, status)


def _signed_in(request: Request, login: Any) -> RedirectResponse:
    drop_previous_session(request)
    response = RedirectResponse("/", status_code=303)
    cookie_codec(request).set(response, login)
    return response


@pages_router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return render(request, "login.html")


@pages_router.post("/login", response_model=None)
def login_form(request: Request, username: FormText = "", password: FormText = "") -> Response:
    limit_auth(request)
    try:
        result = auth_service(request).login(username, password)
    except AppError as exc:
        context = {"error": exc.message, "username": username}
        return render(request, "login.html", context, exc.status)
    return _signed_in(request, result)


@pages_router.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return render(request, "register.html")


@pages_router.post("/register", response_model=None)
def register_form(request: Request, username: FormText = "", password: FormText = "") -> Response:
    limit_auth(request)
    try:
        result = auth_service(request).register(username, password)
    except AppError as exc:
        context = {"error": exc.message, "username": username}
        return render(request, "register.html", context, exc.status)
    return _signed_in(request, result)


@pages_router.post("/logout")
def logout_form(auth: CsrfUser, request: Request) -> RedirectResponse:
    auth_service(request).logout(auth.token)
    response = RedirectResponse("/login", status_code=303)
    cookie_codec(request).clear(response)
    return response


@pages_router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    content: LoadedContent = request.app.state.content
    counts = Counter(p.topic for p in servable(content))
    topics = [
        {"id": t.topic_id, "title": t.title, "section": t.section, "servable": counts[t.topic_id]}
        for t in sorted(content.bundle.topics, key=lambda t: t.order)
    ]
    user = optional_user(request)
    history = practice_service(request).session_summary(user.user_id) if user else []
    titles = {t["id"]: t["title"] for t in topics}
    rows = [
        {
            "session_id": s.session_id,
            "topics": ", ".join(str(titles.get(t, t)) for t in s.topics),
            "started": s.started_at.strftime("%Y-%m-%d %H:%M UTC"),
            "answered": s.answered,
            "correct": s.correct,
        }
        for s in history
    ]
    return render(request, "index.html", {"topics": topics, "history": rows})


@pages_router.post("/sessions")
def start_form(
    auth: CsrfUser, request: Request, topics: Annotated[list[str] | None, Form()] = None
) -> RedirectResponse:
    session_id = practice_service(request).start_session(auth.user_id, (topics or [])[:3])
    return RedirectResponse(f"/practice/{session_id}", status_code=303)


@pages_router.get("/practice/{session_id}", response_model=None)
def practice_page(session_id: int, request: Request) -> Response:
    user = optional_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    practice_service(request).current_item(user.user_id, session_id)  # 403 / 404 as the API
    return render(request, "practice.html", {"session_id": session_id})
