"""Application errors. The web layer maps each to ``{error: code, message}`` with its status."""

from __future__ import annotations


class AppError(Exception):
    status: int = 400
    code: str = "bad_request"

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.code)
        if code is not None:
            self.code = code

    @property
    def message(self) -> str:
        return str(self)


class Unauthorized(AppError):
    status = 401
    code = "unauthorized"


class Forbidden(AppError):
    status = 403
    code = "forbidden"


class NotFound(AppError):
    status = 404
    code = "not_found"


class StaleItem(AppError):
    status = 409
    code = "stale_item"


class InvalidAction(AppError):
    status = 409
    code = "invalid_action"


class InvalidInput(InvalidAction):
    """Well-formed request whose values break a rule (username pattern, password length)."""

    status = 422
    code = "invalid_input"


class Conflict(AppError):
    status = 409
    code = "conflict"


class RateLimited(AppError):
    status = 429
    code = "rate_limited"


class Busy(AppError):
    status = 503
    code = "verifier_busy"


class SubmissionPending(AppError):
    """The same submission id is still being graded (ruling R13); retry shortly."""

    status = 409
    code = "submission_pending"
    retry_after_s = 1
