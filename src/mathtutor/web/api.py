"""JSON routes. Each one calls an application service; none holds session rules."""

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from mathtutor.application.auth import AuthService
from mathtutor.application.errors import (
    Forbidden,
    HelpLimited,
    InvalidInput,
    NotFound,
    StaleItem,
    Unauthorized,
)
from mathtutor.application.practice import Done, ItemView, PracticeService
from mathtutor.domain import AnswerKind
from mathtutor.help import messages as help_messages
from mathtutor.help.service import HelpIn, HelpService, HelpStatus
from mathtutor.jsonio import JsonTooDeep, loads_exact
from mathtutor.verify.structure import check_structure
from mathtutor.verify.types import FormatIssue, SubmittedAnswer, Verdict
from mathtutor.web.messages import format_issue_message
from mathtutor.web.schemas import (
    ActionRequest,
    AuthUser,
    ChoiceAnswerIn,
    ConfusionOut,
    Credentials,
    CurrentResponse,
    ErrorBody,
    FormatIssueOut,
    HelpAvailabilityOut,
    HelpRequest,
    HelpResponse,
    HelpStatusName,
    PublicChoice,
    PublicItem,
    SessionSummaryOut,
    SourceRefOut,
    StartRequest,
    StartResponse,
    SubmissionRequest,
    SubmitResponse,
    VerdictOut,
)
from mathtutor.web.security import CookieCodec, CsrfUser, CurrentUser, RateLimiter, client_ip

auth_router = APIRouter(prefix="/api/auth")


def auth_service(request: Request) -> AuthService:
    service: AuthService = request.app.state.auth
    return service


def cookie_codec(request: Request) -> CookieCodec:
    codec: CookieCodec = request.app.state.cookies
    return codec


def limit_auth(request: Request) -> None:
    limiter: RateLimiter = request.app.state.auth_limiter
    limiter.hit(client_ip(request))


@auth_router.post("/register")
def register(body: Credentials, request: Request, response: Response) -> AuthUser:
    limit_auth(request)
    result = auth_service(request).register(body.username, body.password)
    drop_previous_session(request)
    cookie_codec(request).set(response, result)
    return AuthUser(username=_username(request, result.user_id), csrf_token=result.csrf_token)


@auth_router.post("/login")
def login(body: Credentials, request: Request, response: Response) -> AuthUser:
    limit_auth(request)
    result = auth_service(request).login(body.username, body.password)
    drop_previous_session(request)
    cookie_codec(request).set(response, result)
    return AuthUser(username=_username(request, result.user_id), csrf_token=result.csrf_token)


@auth_router.post("/logout")
def logout(auth: CsrfUser, request: Request, response: Response) -> dict[str, bool]:
    auth_service(request).logout(auth.token)
    cookie_codec(request).clear(response)
    return {"ok": True}


@auth_router.get("/me")
def me(auth: CurrentUser, request: Request) -> AuthUser:
    return AuthUser(username=_username(request, auth.user_id), csrf_token=auth.csrf_token)


def drop_previous_session(request: Request) -> None:
    """Session rotation: the cookie's old server-side row is deleted on login."""
    old = cookie_codec(request).token(request)
    if old is not None:
        auth_service(request).logout(old)


def _username(request: Request, user_id: int) -> str:
    name = auth_service(request).username(user_id)
    if name is None:
        raise Unauthorized("Please sign in.")
    return name


# -- practice -------------------------------------------------------------------------------

practice_router = APIRouter(prefix="/api/sessions")
# MathJSON may nest 30 levels (spec 03); the request wrapper adds 3. Checked before parsing.
MAX_JSON_DEPTH = 40
_answers = logging.getLogger("mathtutor.answers")


def practice_service(request: Request) -> PracticeService:
    service: PracticeService = request.app.state.practice
    return service


def help_service(request: Request) -> HelpService:
    service: HelpService = request.app.state.help
    return service


def help_availability(request: Request, user_id: int, view: ItemView) -> HelpAvailabilityOut | None:
    """Null while help is not enabled, so a disabled deployment looks exactly as before."""
    service = help_service(request)
    if not service.enabled:
        return None
    a = service.availability(view, user_id)
    return HelpAvailabilityOut(
        enabled=a.enabled,
        types=list(a.types),
        confusions=[ConfusionOut(id=c.id, label=c.label) for c in a.confusions],
        hint_level=a.hint_level,
    )


def to_public(view: ItemView, help_: HelpAvailabilityOut | None = None) -> PublicItem:
    return PublicItem(
        session_item_id=view.session_item_id,
        revision=view.revision,
        statement_html=view.statement_html,
        answer_kind=view.answer_kind.value,
        precision_hint=view.precision_hint,
        choices=None
        if view.choices is None
        else [PublicChoice(id=i, label_latex=label) for i, label in view.choices],
        source=view.source,
        allowed_actions=view.allowed_actions,
        tries_left=view.tries_left,
        help=help_,
    )


def public_item(request: Request, user_id: int, view: ItemView) -> PublicItem:
    return to_public(view, help_availability(request, user_id, view))


def to_current(request: Request, user_id: int, result: ItemView | Done) -> CurrentResponse:
    if isinstance(result, Done):
        return CurrentResponse(item=None, done=True, reason=result.reason)
    return CurrentResponse(
        item=public_item(request, user_id, result),
        done=False,
        revealed_latex=result.revealed_latex,
    )


def _outcome(outcome: Verdict | FormatIssue) -> VerdictOut | FormatIssueOut:
    if isinstance(outcome, FormatIssue):
        return FormatIssueOut(
            code=outcome.code.value, message=format_issue_message(outcome.code, outcome.detail)
        )
    return VerdictOut(
        status=outcome.status.value, reason=outcome.reason.value, method=outcome.method.value
    )


@practice_router.post("", status_code=201)
def start_session(body: StartRequest, auth: CsrfUser, request: Request) -> StartResponse:
    return StartResponse(
        session_id=practice_service(request).start_session(auth.user_id, body.topics)
    )


@practice_router.get("")
def list_sessions(auth: CurrentUser, request: Request) -> list[SessionSummaryOut]:
    return [
        SessionSummaryOut(
            session_id=s.session_id,
            topics=s.topics,
            started_at=s.started_at,
            answered=s.answered,
            correct=s.correct,
        )
        for s in practice_service(request).session_summary(auth.user_id)
    ]


@practice_router.get("/{session_id}/current")
def current(session_id: int, auth: CurrentUser, request: Request) -> CurrentResponse:
    return to_current(
        request, auth.user_id, practice_service(request).current_item(auth.user_id, session_id)
    )


@practice_router.post("/{session_id}/submit")
async def submit(session_id: int, auth: CsrfUser, request: Request) -> SubmitResponse:
    limiter: RateLimiter = request.app.state.submit_limiter
    limiter.hit(str(auth.user_id))
    try:
        req = SubmissionRequest.model_validate(
            loads_exact(await request.body(), max_depth=MAX_JSON_DEPTH)
        )
    except (ValueError, ValidationError) as exc:  # ValidationError is a ValueError
        raise InvalidInput(_bad_body(exc), code="invalid_request") from None
    answer = req.answer
    service = practice_service(request)
    if not isinstance(answer, ChoiceAnswerIn):
        # Cheap bounds in the web process, before any pool work (spec 03).
        issue = check_structure(answer.mathjson)
        if issue is not None:
            view = await run_in_threadpool(service.current_item, auth.user_id, session_id)
            if isinstance(view, Done) or view.session_item_id != req.session_item_id:
                raise StaleItem("This problem changed; reload it.")
            item = await run_in_threadpool(public_item, request, auth.user_id, view)
            return SubmitResponse(outcome=_outcome(issue), item=item, replayed=False)
    submitted = SubmittedAnswer(
        kind=AnswerKind(answer.kind),
        mathjson=None if isinstance(answer, ChoiceAnswerIn) else answer.mathjson,
        latex="" if isinstance(answer, ChoiceAnswerIn) else answer.latex,
        choice_id=answer.choice_id if isinstance(answer, ChoiceAnswerIn) else None,
    )
    _answers.debug("submit %s: %r", req.submission_id, submitted)
    result = await run_in_threadpool(
        service.submit_answer,
        auth.user_id,
        session_id,
        req.submission_id,
        req.session_item_id,
        req.item_revision,
        submitted,
    )
    if isinstance(result.outcome, Verdict):
        request.state.log = {
            "verdict_status": result.outcome.status.value,
            "verdict_reason": result.outcome.reason.value,
            "verdict_method": result.outcome.method.value,
            "replayed": result.replayed,
            "worker_ms": result.worker_ms,
            "queue_ms": result.queue_ms,
        }
    else:
        request.state.log = {"format_issue": result.outcome.code.value}
    item = await run_in_threadpool(public_item, request, auth.user_id, result.item)
    return SubmitResponse(outcome=_outcome(result.outcome), item=item, replayed=result.replayed)


def _bad_body(exc: Exception) -> str:
    if isinstance(exc, JsonTooDeep):
        return "The answer is nested too deeply to check."
    if isinstance(exc, ValidationError):
        fields = sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()})
        return "Invalid request" + (f": {', '.join(fields)}" if fields else "") + "."
    return "The request body is not valid JSON."


@practice_router.post("/{session_id}/advance")
def advance(
    session_id: int, body: ActionRequest, auth: CsrfUser, request: Request
) -> CurrentResponse:
    return to_current(
        request,
        auth.user_id,
        practice_service(request).advance(
            auth.user_id, session_id, body.session_item_id, body.item_revision
        ),
    )


@practice_router.post("/{session_id}/skip")
def skip(session_id: int, body: ActionRequest, auth: CsrfUser, request: Request) -> CurrentResponse:
    return to_current(
        request,
        auth.user_id,
        practice_service(request).skip(
            auth.user_id, session_id, body.session_item_id, body.item_revision
        ),
    )


@practice_router.post("/{session_id}/reveal")
def reveal(
    session_id: int, body: ActionRequest, auth: CsrfUser, request: Request
) -> CurrentResponse:
    return to_current(
        request,
        auth.user_id,
        practice_service(request).reveal(
            auth.user_id, session_id, body.session_item_id, body.item_revision
        ),
    )


# -- help -----------------------------------------------------------------------------------

help_router = APIRouter(prefix="/api/help")


@help_router.post("", responses={202: {"model": HelpResponse}, 429: {"model": ErrorBody}})
def request_help(
    body: HelpRequest, auth: CsrfUser, request: Request, response: Response
) -> HelpResponse:
    """200 with the finished outcome, 202 while the item's help is in flight, 409 for a stale
    revision or a reused request id, 429 ``help_limited``. Someone else's item is a 404.
    Runs in the thread pool: the provider call blocks for seconds."""
    req = HelpIn(
        help_request_id=body.help_request_id,
        session_item_id=body.session_item_id,
        item_revision=body.item_revision,
        help_type=body.help_type,
        confusion=body.confusion,
    )
    try:
        outcome = help_service(request).request_help(auth.user_id, req)
    except Forbidden:
        raise NotFound(help_messages.PROBLEM_NOT_FOUND) from None
    request.state.log = {"help_type": body.help_type, "help_status": outcome.status.value}
    if outcome.status is HelpStatus.LIMITED:
        raise HelpLimited("limited", help_messages.LIMITED)
    if outcome.status is HelpStatus.PENDING:
        response.status_code = 202
    return HelpResponse(
        request_id=outcome.request_id,
        status=cast(HelpStatusName, outcome.status.value),
        session_item_id=outcome.session_item_id,
        item_revision=outcome.item_revision,
        help_seq=outcome.help_seq,
        hint_level=outcome.hint_level,
        html=outcome.html,
        sources=[
            SourceRefOut(label=r.label, url=r.url, license=r.license) for r in outcome.sources
        ],
    )
