"""Request and result types shared by the web process and verifier workers (no SymPy)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import JsonValue

from mathtutor.content.schema import Answer
from mathtutor.domain import AnswerKind, FormatIssueCode, Method, VerdictReason, VerdictStatus


@dataclass(frozen=True)
class SubmittedAnswer:
    kind: AnswerKind
    mathjson: JsonValue | None
    latex: str
    choice_id: str | None


@dataclass(frozen=True)
class Verdict:
    status: VerdictStatus
    reason: VerdictReason
    method: Method


@dataclass(frozen=True)
class FormatIssue:
    code: FormatIssueCode
    detail: str = ""


@dataclass(frozen=True)
class CheckRequest:
    answer_spec: Answer
    answer: SubmittedAnswer
    request_id: str = ""


@dataclass(frozen=True)
class CheckResult:
    outcome: Verdict | FormatIssue
    verifier_version: str
    worker_ms: int = 0
    queue_ms: int = 0


class VerifierBusy(Exception):
    """The worker queue is full or the queue wait expired."""
