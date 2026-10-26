"""Fail-closed leak guard: does Claude-written help text contain the problem's answer?

Runs in the web process, so it never imports SymPy, mpmath or ``mathtutor.verify.check``.
Math is found in the text (``$..$``, ``$$..$$``, ``\\(..\\)``, ``\\[..\\]``, the right side of
a prose ``=`` and prose decimals), read by the allowlist parser (``latex_parse``), and each
distinct tree is sent as a ``CheckRequest`` to the guard's own verifier pool, against an
``ExpressionAnswer`` built from the reference (always ``strict_domain=False``).

Anything the guard cannot check blocks the text: a rejected parse, a busy pool, a spent
deadline, an abstaining checker, unbalanced delimiters or too many candidates.
``GuardResult`` holds counts and a fixed reason code only, never text.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from mathtutor.application.practice import Pool
from mathtutor.content.schema import Answer, ChoiceAnswer, Decimals, ExpressionAnswer, NumericAnswer
from mathtutor.domain import AnswerKind, VerdictReason, VerdictStatus
from mathtutor.help.config import GuardLimits
from mathtutor.help.latex_parse import ParseRejected, parse_latex
from mathtutor.verify.types import CheckRequest, CheckResult, SubmittedAnswer, Verdict, VerifierBusy


class LeakStatus(StrEnum):
    LEAK = "leak"
    NO_MATCH = "no_match"
    UNCHECKED = "unchecked"


Origin = Literal["inline", "display", "equation_rhs", "decimal"]
GuardDecision = Literal["pass", "no_detected_math", "block"]


@dataclass(frozen=True)
class Candidate:
    latex: str
    origin: Origin


def _zero_counts() -> dict[LeakStatus, int]:
    return dict.fromkeys(LeakStatus, 0)


@dataclass(frozen=True)
class GuardResult:
    """Counts and a reason code only: no LaTeX, student or model text.

    ``counts[NO_MATCH]`` includes candidates with foreign symbols (never sent to the checker);
    ``foreign`` counts those separately.
    """

    decision: GuardDecision
    counts: dict[LeakStatus, int] = field(default_factory=_zero_counts)
    reason: str = ""
    foreign: int = 0


class MalformedMath(ValueError):
    """A math delimiter is unbalanced; the text cannot be split into prose and math."""


# -- extraction ------------------------------------------------------------------------------

_SENTINEL = "\x00"  # stands for a math span inside the prose
_PROSE_PUNCT = ".,;:!?"
_PROSE_DECIMAL = re.compile(r"(?<![\w.])-?\d*\.\d+(?![\w]|\.\d)")


def _find(text: str, start: int, closer: str) -> int:
    """Index of ``closer`` at or after ``start``, skipping backslash escapes, or -1."""
    k = start
    while k < len(text):
        if text.startswith(closer, k):
            return k
        k += 2 if text[k] == "\\" else 1
    return -1


def _clean(piece: str) -> str:
    """Trim spaces and trailing prose punctuation (``x^2.``), keeping ``\\,``-style spacing."""
    piece = piece.strip()
    while piece and piece[-1] in _PROSE_PUNCT and not piece[:-1].endswith("\\"):
        piece = piece[:-1].rstrip()
    return piece


def _split_math(text: str) -> tuple[list[Candidate], str]:
    """Math spans as candidates (split on ``=``), and the prose with each span as a sentinel."""
    math: list[Candidate] = []
    prose: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        nxt = text[i + 1 : i + 2]
        if c == "\\" and nxt in ("(", "["):
            closer, origin = ("\\)", "inline") if nxt == "(" else ("\\]", "display")
            start = i + 2
        elif c == "\\" and nxt in (")", "]"):
            raise MalformedMath("closing delimiter without an opener")
        elif c == "\\":
            prose.append(text[i : i + 2])  # an escape such as \$ is prose
            i += 2
            continue
        elif c == "$":
            double = text.startswith("$$", i)
            closer, origin = ("$$", "display") if double else ("$", "inline")
            start = i + len(closer)
        else:
            prose.append(c)
            i += 1
            continue
        end = _find(text, start, closer)
        if end < 0:
            raise MalformedMath("unbalanced math delimiter")
        for side in text[start:end].split("="):
            latex = _clean(side)
            if latex:
                math.append(Candidate(latex, origin))  # type: ignore[arg-type]
        prose.append(_SENTINEL)
        i = end + len(closer)
    return math, "".join(prose)


def _prose_candidates(prose: str) -> list[Candidate]:
    """The right side of each prose ``=`` (to the next ``=``, math span or line end), then
    decimal literals in the remaining prose."""
    rhs: list[Candidate] = []
    rest: list[str] = []
    for line in prose.split("\n"):
        head, *sides = line.split("=")
        rest.append(head)
        for side in sides:
            piece, _, after = side.partition(_SENTINEL)
            latex = _clean(piece)
            if latex:
                rhs.append(Candidate(latex, "equation_rhs"))
            rest.append(after)
    decimals = [
        Candidate(m.group(), "decimal")
        for chunk in rest
        for m in _PROSE_DECIMAL.finditer(chunk.replace(_SENTINEL, " "))
    ]
    return rhs + decimals


def extract_candidates(text: str, limits: GuardLimits) -> list[Candidate] | None:
    """Every math candidate in ``text``, in order: delimited math, prose equations, decimals.

    Returns None when there are more than ``limits.max_candidates``. Raises ``MalformedMath``
    for an unbalanced delimiter.
    """
    math, prose = _split_math(text)
    found = math + _prose_candidates(prose)
    return None if len(found) > limits.max_candidates else found


# -- classification --------------------------------------------------------------------------

_LEAK_REASONS = frozenset(
    {
        VerdictReason.STUDENT_UNDEFINED,
        VerdictReason.UNDEFINED_ON_DOMAIN,
        VerdictReason.POLE_ON_DOMAIN,
    }
)


def classify(result: CheckResult) -> LeakStatus:
    """A checker outcome as a leak status. Formula equality counts before the domain, so the
    domain-only mismatches are leaks; anything outside the table is unchecked."""
    outcome = result.outcome
    if not isinstance(outcome, Verdict):
        return LeakStatus.UNCHECKED
    if outcome.status == VerdictStatus.CORRECT:
        return LeakStatus.LEAK
    if outcome.status == VerdictStatus.INCORRECT:
        if outcome.reason == VerdictReason.COUNTEREXAMPLE:
            return LeakStatus.NO_MATCH
        if outcome.reason in _LEAK_REASONS:
            return LeakStatus.LEAK
    return LeakStatus.UNCHECKED


# -- the guard -------------------------------------------------------------------------------

_DECIMAL_2 = re.compile(r"\d*\.\d{2,}")


def _reference(answer: Answer) -> ExpressionAnswer:
    if isinstance(answer, ChoiceAnswer):
        choice = next(c for c in answer.choices if c.id == answer.correct)
        return ExpressionAnswer(kind="expression", latex=choice.latex, mathjson=choice.mathjson)
    return ExpressionAnswer(
        kind="expression",
        latex=answer.latex,
        mathjson=answer.mathjson,
        variable=answer.variable,
        domain=answer.domain,
        strict_domain=False,
    )


def _rule_violation(text: str, answer: Answer) -> str | None:
    """Deterministic rules checked before any worker call."""
    if isinstance(answer, ChoiceAnswer):
        letter = re.escape(answer.correct)
        by_name = re.compile(rf"\b(option|choice|answer)\s*\(?{letter}\)?\b", re.IGNORECASE)
        in_parens = re.compile(rf"\({letter}\)", re.IGNORECASE)
        if by_name.search(text) or in_parens.search(text):
            return "choice_reference"
    if (
        isinstance(answer, NumericAnswer)
        and isinstance(answer.precision, Decimals)
        and _DECIMAL_2.search(text)
    ):
        return "decimal_literal"
    return None


class LeakGuard:
    """Checks help text against a problem's answer through a dedicated verifier pool."""

    def __init__(
        self,
        pool: Pool,
        limits: GuardLimits,
        clock: Callable[[], float],
    ) -> None:
        self._pool = pool
        self._limits = limits
        self._clock = clock

    def check(self, text: str, answer: Answer, deadline: float) -> GuardResult:
        """Decide whether ``text`` may be delivered. ``deadline`` is on ``clock``'s scale; the
        guard also stops after ``limits.budget_s``."""
        rule = _rule_violation(text, answer)
        if rule is not None:
            return GuardResult("block", reason=rule)
        try:
            candidates = extract_candidates(text, self._limits)
        except MalformedMath:
            return GuardResult("block", reason="malformed_math")
        if candidates is None:
            return GuardResult("block", reason="too_many_candidates")
        if not candidates:
            return GuardResult("no_detected_math", reason="no_detected_math")

        deadline = min(deadline, self._clock() + self._limits.budget_s)
        reference = _reference(answer)
        counts = _zero_counts()
        foreign = 0
        seen: set[str] = set()
        sent = 0
        for candidate in candidates:
            parsed = parse_latex(candidate.latex, variable=reference.variable)
            if isinstance(parsed, ParseRejected):
                status, reason = LeakStatus.UNCHECKED, "parse_rejected"
            else:
                key = json.dumps(parsed.tree, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                if parsed.foreign:
                    counts[LeakStatus.NO_MATCH] += 1
                    foreign += 1
                    continue
                if self._clock() >= deadline:
                    status, reason = LeakStatus.UNCHECKED, "deadline"
                else:
                    sent += 1
                    request = CheckRequest(
                        answer_spec=reference,
                        # The guard's own parse is the reading; no model text leaves the process.
                        answer=SubmittedAnswer(AnswerKind.EXPRESSION, parsed.tree, "", None),
                        request_id=f"guard:{sent}",
                    )
                    status, reason = self._submit(request)
            counts[status] += 1
            if status is not LeakStatus.NO_MATCH:
                return GuardResult("block", counts, reason, foreign)
        return GuardResult("pass", counts, "checked", foreign)

    def _submit(self, request: CheckRequest) -> tuple[LeakStatus, str]:
        try:
            result = self._pool.submit(request)
        except VerifierBusy:
            return LeakStatus.UNCHECKED, "verifier_busy"
        except Exception:  # fail closed: any surprise blocks the text
            return LeakStatus.UNCHECKED, "verifier_error"
        status = classify(result)
        return status, {LeakStatus.LEAK: "leak", LeakStatus.UNCHECKED: "unverified"}.get(status, "")
