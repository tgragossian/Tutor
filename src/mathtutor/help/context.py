"""Help request context (types only; the DB-backed builder arrives with the service)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from mathtutor.domain import AnswerKind, VerdictStatus

HelpType = Literal["hint", "feedback", "explain"]


@dataclass(frozen=True)
class AttemptLine:
    latex: str
    status: VerdictStatus


@dataclass(frozen=True)
class HelpContext:
    problem_id: str
    topic: str
    section: str
    statement: str
    answer_kind: AnswerKind
    attempts: list[AttemptLine]
    tries_used: int
    hint_level: int
    misconception_note: str | None
    variable: str
