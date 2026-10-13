"""Domain enums shared by content, session and web layers."""

from __future__ import annotations

from enum import StrEnum

MAX_TRIES = 3


class AnswerKind(StrEnum):
    EXPRESSION = "expression"
    NUMERIC = "numeric"
    CHOICE = "choice"


class ReviewStatus(StrEnum):
    HUMAN_VERIFIED = "human_verified"
    NEEDS_REVIEW = "needs_review"


class ItemState(StrEnum):
    ACTIVE = "active"
    ANSWERED = "answered"
    EXHAUSTED = "exhausted"
    REVEALED = "revealed"
    COMPLETED = "completed"


class Action(StrEnum):
    SUBMIT = "submit"
    ADVANCE = "advance"
    SKIP = "skip"
    REVEAL = "reveal"


class VerdictStatus(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNABLE_TO_VERIFY = "unable_to_verify"


class FormatIssueCode(StrEnum):
    EMPTY = "empty"
    INCOMPLETE = "incomplete"
    EXACT_REQUIRED = "exact_required"
    INPUT_TOO_LARGE = "input_too_large"
    UNSUPPORTED_NOTATION = "unsupported_notation"
