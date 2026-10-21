"""Structured request logs and the request body cap (pure ASGI, spec 07).

One JSON line per request: request id, method, route template, status and duration, plus any
fields a route puts in ``request.state.log`` (the submit route adds verdict fields). Never
logged: passwords, cookies, CSRF tokens. Answers are logged only at DEBUG, by the routes.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from typing import Any

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ACCESS_LOGGER = "mathtutor.access"
MAX_BODY_BYTES = 16 * 1024


class _StderrHandler(logging.Handler):
    """Writes to whatever ``sys.stderr`` is at emit time (container logs, test capture)."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            sys.stderr.write(self.format(record) + "\n")
        except Exception:  # noqa: BLE001 - logging must never break a request
            self.handleError(record)


def access_logger() -> logging.Logger:
    logger = logging.getLogger(ACCESS_LOGGER)
    if not any(isinstance(h, _StderrHandler) for h in logger.handlers):
        logger.addHandler(_StderrHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


class RequestLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = access_logger()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        state: dict[str, Any] = scope.setdefault("state", {})
        state["request_id"] = request_id
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [*message.get("headers", []), (b"x-request-id", request_id.encode())]
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            route = scope.get("route")
            entry: dict[str, Any] = {
                "request_id": request_id,
                "method": scope.get("method"),
                "route": getattr(route, "path", None) or scope.get("path"),
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            }
            extra = state.get("log")
            if isinstance(extra, dict):
                entry.update(extra)
            self.logger.info(json.dumps(entry, default=str))


class BodyLimitMiddleware:
    """Rejects bodies over 16 KB: from Content-Length up front, else while the body is read."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = dict(scope.get("headers", [])).get(b"content-length")
        if declared is not None and declared.isdigit() and int(declared) > self.max_bytes:
            await _send_413(send)
            return
        seen = 0

        async def counted() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max_bytes:
                    # An HTTPException survives FastAPI's body parsing (others become 400).
                    raise HTTPException(413, _TOO_LARGE)
            return message

        await self.app(scope, counted, send)


_TOO_LARGE = "The request body is larger than 16 KB."


async def _send_413(send: Send) -> None:
    body = json.dumps({"error": "payload_too_large", "message": _TOO_LARGE}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
