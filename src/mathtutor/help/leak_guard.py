"""Fail-closed leak guard: does Claude-written help text contain the problem's answer?

Runs in the web process, so it never imports SymPy, mpmath or ``mathtutor.verify.check``.
Math is found in the text (``$..$``, ``$$..$$``, ``\\(..\\)``, ``\\[..\\]``, the right side of
a prose ``=``, prose decimals, and every prose number on numeric problems), read by the
allowlist parser (``latex_parse``), and each distinct tree is sent as a ``CheckRequest`` to
the guard's own verifier pool, against an ``ExpressionAnswer`` built from the reference
(always ``strict_domain=False``).

Anything the guard cannot check blocks the text: a rejected parse, a busy pool, a spent
deadline, an abstaining checker, unbalanced delimiters, LaTeX left in the prose or too many
candidates. Single-letter foreign symbols are also checked replaced by the variable and by 0.
``GuardResult`` holds counts and a fixed reason code only, never text.
"""

from __future__ import annotations

import itertools
import json
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from pydantic import JsonValue

from mathtutor.application.practice import Pool
from mathtutor.content.schema import Answer, ChoiceAnswer, Decimals, ExpressionAnswer, NumericAnswer
from mathtutor.domain import AnswerKind, VerdictReason, VerdictStatus
from mathtutor.help.config import GuardLimits
from mathtutor.help.latex_parse import ParsedMath, ParseRejected, parse_latex
from mathtutor.verify.types import CheckRequest, CheckResult, SubmittedAnswer, Verdict, VerifierBusy


class LeakStatus(StrEnum):
    LEAK = "leak"
    NO_MATCH = "no_match"
    UNCHECKED = "unchecked"


Origin = Literal["inline", "display", "equation_rhs", "decimal", "prose_number"]
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
    """A math delimiter is unbalanced, or LaTeX is left in the prose outside any span."""


# -- extraction ------------------------------------------------------------------------------

_SENTINEL = "\x00"  # stands for a math span inside the prose
_PROSE_PUNCT = ".,;:!?"
_PROSE_ESCAPES = frozenset("$%&#")
_MATH_PUNCT = ".,;:?"  # never "!" inside math: $5!$ is a factorial, not 5
_PROSE_DECIMAL = re.compile(r"(?<![\w.])-?\d*\.\d+(?![\w]|\.\d)")
# Numeric problems: signed integers, decimals and simple a/b.
_PROSE_NUMBER = re.compile(
    r"(?<![\w./])([-\u2212]?)((?:\d+(?:\.\d+)?|\.\d+)(?:/\d+)?)(?!\w|[./]\d)"
)
_PROSE_LATEX = re.compile(r"\\[A-Za-z]|[\^_]")


def _find(text: str, start: int, closer: str) -> int:
    """Index of ``closer`` at or after ``start``, skipping backslash escapes, or -1."""
    k = start
    while k < len(text):
        if text.startswith(closer, k):
            return k
        k += 2 if text[k] == "\\" else 1
    return -1


def _clean(piece: str, punct: str = _PROSE_PUNCT) -> str:
    """Trim spaces and trailing prose punctuation (``x^2.``), keeping ``\\,``-style spacing."""
    piece = piece.strip()
    while piece and piece[-1] in punct and not piece[:-1].endswith("\\"):
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
        elif c == "\\" and nxt in _PROSE_ESCAPES:
            prose.append(text[i : i + 2])  # \$, \%, \&, \# are prose characters
            i += 2
            continue
        elif c == "\\":
            # Any other backslash in prose is LaTeX outside a span (\begin, \\( ...).
            raise MalformedMath("LaTeX outside a math span")
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
            latex = _clean(side, _MATH_PUNCT)
            if latex:
                math.append(Candidate(latex, origin))  # type: ignore[arg-type]
        prose.append(_SENTINEL)
        i = end + len(closer)
    return math, "".join(prose)


def _prose_candidates(prose: str, numbers: bool) -> list[Candidate]:
    """The right side of each prose ``=`` (to the next ``=``, math span or line end), then
    decimal literals (with ``numbers``, every number) in the remaining prose."""
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
    chunks = [chunk.replace(_SENTINEL, " ") for chunk in rest]
    if not numbers:
        return rhs + [
            Candidate(m.group(), "decimal") for c in chunks for m in _PROSE_DECIMAL.finditer(c)
        ]
    found: list[Candidate] = []
    for chunk in chunks:
        for m in _PROSE_NUMBER.finditer(chunk):
            sign, magnitude = m.groups()
            if sign:  # "-12" is also checked as "12": a sign slip must not hide the magnitude
                found.append(Candidate("-" + magnitude, "prose_number"))
            found.append(Candidate(magnitude, "prose_number"))
    return rhs + found


def extract_candidates(
    text: str, limits: GuardLimits, *, numbers: bool = False
) -> list[Candidate] | None:
    """Every math candidate in ``text``, in order: delimited math, prose equations, then prose
    decimals, or every prose number when ``numbers`` (numeric problems).

    Returns None when there are more than ``limits.max_candidates``. Raises ``MalformedMath``
    for an unbalanced delimiter or LaTeX (a command, ``^`` or ``_``) left in the prose.
    """
    math, prose = _split_math(text)
    if _PROSE_LATEX.search(prose):
        raise MalformedMath("LaTeX outside a math span")
    found = math + _prose_candidates(prose, numbers)
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


_ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth")
_NUMBERED = ("1st", "2nd", "3rd", "4th", "5th", "6th")
_KEYWORD = r"\b(?:option|choice|answer|pick|select)"
_NOUN = r"(?:option|choice|answer)"
# Between a keyword and the letter: spaces, "is", "would be", "=", ":", emphasis, quotes, dashes.
_FILLER = r"(?:\s|\bis\b|\bwould\s+be\b|[=:*_'\"`‘’“”–—-])*"
_MARKS = r"[*_'\"`‘’“”]"  # emphasis and quotes that can wrap a letter


def _letter_token(letter: str) -> str:
    """The letter as a standalone choice token: ``(a)``, ``**a**``/``'a'``, or a bare ``a``
    followed by closing punctuation or the line end (so the article in "pick a point" is not)."""
    return (
        rf"(?:\(\s*{letter}\s*\)"
        rf"|(?<={_MARKS}){letter}(?={_MARKS})"
        rf"|\b{letter}(?=\s*(?:[).,:;!?]|$)))"
    )


def _choice_patterns(answer: ChoiceAnswer) -> list[re.Pattern[str]]:
    """Ways to name the correct choice: by letter, at a line start, or by its position."""
    letter = re.escape(answer.correct)
    index = [c.id for c in answer.choices].index(answer.correct)
    flags = re.IGNORECASE | re.MULTILINE
    return [
        re.compile(rf"{_KEYWORD}{_FILLER}{_letter_token(letter)}", flags),
        re.compile(rf"\({letter}\)", flags),
        re.compile(rf"^\s*\(?{letter}[).]", flags),
        re.compile(rf"\b{_ORDINALS[index]}\s+{_NOUN}", flags),
        re.compile(rf"\b{_NUMBERED[index]}\b", flags),
        re.compile(rf"\b{_NOUN}\s*#?\s*{index + 1}\b", flags),
    ]


def _rule_violation(text: str, answer: Answer) -> str | None:
    """Deterministic rules checked before any worker call."""
    if isinstance(answer, ChoiceAnswer):
        if any(p.search(text) for p in _choice_patterns(answer)):
            return "choice_reference"
    if (
        isinstance(answer, NumericAnswer)
        and isinstance(answer.precision, Decimals)
        and _DECIMAL_2.search(text)
    ):
        return "decimal_literal"
    return None


def _substitutable(parsed: ParsedMath) -> frozenset[str] | None:
    """The foreign names when every one is a single-letter symbol, else None. A letter used
    as a function name (``f(x)``) or any other foreign item (``y'``, ``du/dx``, Greek) keeps
    the candidate unchecked as a no match."""
    functions: set[str] = set()
    stack: list[JsonValue] = [parsed.tree]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            if node and node[0] == "Apply" and len(node) > 1 and isinstance(node[1], str):
                functions.add(node[1])
            stack.extend(node[1:])
    letters = parsed.foreign
    if all(len(n) == 1 and n.isascii() and n.isalpha() for n in letters) and not (
        letters & functions
    ):
        return letters
    return None


def _substitute(tree: JsonValue, letters: frozenset[str], value: str | int) -> JsonValue:
    """``tree`` with every symbol in ``letters`` replaced by ``value`` (heads untouched)."""
    if isinstance(tree, str):
        return value if tree in letters else tree
    if isinstance(tree, list) and tree:
        return [tree[0], *(_substitute(operand, letters, value) for operand in tree[1:])]
    return tree


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
            numbers = isinstance(answer, NumericAnswer)
            candidates = extract_candidates(text, self._limits, numbers=numbers)
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
        ids = itertools.count(1)
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
                    status, reason = self._check_foreign(parsed, reference, deadline, ids)
                    if status is LeakStatus.NO_MATCH:
                        foreign += 1
                else:
                    status, reason = self._check_tree(parsed.tree, reference, deadline, ids)
            counts[status] += 1
            if status is not LeakStatus.NO_MATCH:
                return GuardResult("block", counts, reason, foreign)
        return GuardResult("pass", counts, "checked", foreign)

    def _check_foreign(
        self,
        parsed: ParsedMath,
        reference: ExpressionAnswer,
        deadline: float,
        ids: Iterator[int],
    ) -> tuple[LeakStatus, str]:
        """A tree with foreign names is never checked as written. When every foreign name is a
        single-letter symbol, it is also checked with them all replaced by the variable, then
        by 0 (``2t``, ``2x + C``); only a leak there counts, otherwise it stays a no match."""
        letters = _substitutable(parsed)
        if letters is None:
            return LeakStatus.NO_MATCH, ""
        for value in (reference.variable, 0):
            tree = _substitute(parsed.tree, letters, value)
            status, reason = self._check_tree(tree, reference, deadline, ids)
            if status is LeakStatus.LEAK:
                return status, reason
        return LeakStatus.NO_MATCH, ""

    def _check_tree(
        self, tree: JsonValue, reference: ExpressionAnswer, deadline: float, ids: Iterator[int]
    ) -> tuple[LeakStatus, str]:
        if self._clock() >= deadline:
            return LeakStatus.UNCHECKED, "deadline"
        request = CheckRequest(
            answer_spec=reference,
            # The guard's own parse is the reading; no model text leaves the process.
            answer=SubmittedAnswer(AnswerKind.EXPRESSION, tree, "", None),
            request_id=f"guard:{next(ids)}",
        )
        return self._submit(request)

    def _submit(self, request: CheckRequest) -> tuple[LeakStatus, str]:
        try:
            result = self._pool.submit(request)
        except VerifierBusy:
            return LeakStatus.UNCHECKED, "verifier_busy"
        except Exception:  # fail closed: any surprise blocks the text
            return LeakStatus.UNCHECKED, "verifier_error"
        status = classify(result)
        return status, {LeakStatus.LEAK: "leak", LeakStatus.UNCHECKED: "unverified"}.get(status, "")
