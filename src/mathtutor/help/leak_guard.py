"""Fail-closed leak guard: does Claude-written help text contain the problem's answer?

Runs in the web process, so it never imports SymPy, mpmath or ``mathtutor.verify.check``.
Math is found in the text (``$..$``, ``$$..$$``, ``\\(..\\)``, ``\\[..\\]``, the right side of
a prose ``=``, prose decimals, and every prose number on numeric problems), read by the
allowlist parser (``latex_parse``), and each distinct tree is sent as a ``CheckRequest`` to
the guard's own verifier pool, against an ``ExpressionAnswer`` built from the reference
(always ``strict_domain=False``).

Anything the guard cannot check blocks the text: a rejected parse, a busy pool, a spent
deadline, an abstaining checker, unbalanced delimiters, LaTeX left in the prose or too many
candidates. Single-letter foreign symbols are also checked replaced by the variable and by 0
(and by 1 on numeric problems); any such variant left unchecked blocks too.
``GuardResult`` holds counts and a fixed reason code only, never text.
"""

from __future__ import annotations

import bisect
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


Origin = Literal["inline", "display", "equation_rhs", "decimal", "prose_number", "prose_term"]
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
# Numeric problems: signed integers, decimals and simple a/b (``12 / 121``, ``200÷343``,
# ``(-200)/343``, ``-(200/343)``, ``200/(343)``), kept as an unsigned magnitude; the guard
# checks both signs. ``1,200`` (thousands separators) is one number; ``1, 2, 3`` is three.
_INT = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
_NUM = rf"(?:{_INT}(?:\.\d+)?|\.\d+)"
_DEN = rf"(?:\(\s*{_INT}\s*\)|{_INT})"
_SIGN = r"[-−]?"
_OVER = r"\s*[/÷]\s*"
_PROSE_NUMBER = re.compile(
    rf"(?<![\w./÷])(?:"
    rf"{_SIGN}\(\s*{_SIGN}(?P<n1>{_NUM})\s*\){_OVER}(?P<d1>{_DEN})"
    rf"|{_SIGN}\(\s*{_SIGN}(?P<n2>{_NUM}){_OVER}(?P<d2>{_DEN})\s*\)"
    rf"|{_SIGN}(?P<n3>{_NUM})(?:{_OVER}(?P<d3>{_DEN}))?"
    rf")(?!\w|\.\d|{_OVER}[\d(])"
)
# ``2nd``, ``1st``, ``3rd``, ``12th``: an ordinal, not a number (R14).
_ORDINAL = re.compile(r"(?<![\w.])\d+(?:st|nd|rd|th)(?!\w)")
_DIGITS = re.compile(r"\d+")
_CHUNK_BREAK = "\x01"  # joins the prose pieces of one line; no number spans it
# Expression problems: a coefficient glued to a letter (``2x``).
_PROSE_TERM = re.compile(r"(?<![\w.])\d+[a-zA-Z](?!\w)")
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


SpanKind = Literal["prose", "inline", "display"]


def split_spans(text: str) -> list[tuple[SpanKind, str]]:
    """``text`` as prose pieces and math spans, in order, exactly as the guard reads it.

    A math span's content excludes its delimiters; prose keeps its ``\\$``-style escapes.
    Raises ``MalformedMath`` like ``extract_candidates``. The help renderer uses this so that
    it never renders as math anything the guard did not check as math.
    """
    spans: list[tuple[SpanKind, str]] = []
    prose: list[str] = []

    def flush() -> None:
        if prose:
            spans.append(("prose", "".join(prose)))
            prose.clear()

    i = 0
    while i < len(text):
        c = text[i]
        nxt = text[i + 1 : i + 2]
        origin: SpanKind
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
        flush()
        spans.append((origin, text[start:end]))
        i = end + len(closer)
    flush()
    return spans


def _split_math(text: str) -> tuple[list[Candidate], str]:
    """Math spans as candidates (split on ``=``), and the prose with each span as a sentinel."""
    math: list[Candidate] = []
    prose: list[str] = []
    for kind, content in split_spans(text):
        if kind == "prose":
            prose.append(content)
            continue
        for side in content.split("="):
            latex = _clean(side, _MATH_PUNCT)
            if latex:
                math.append(Candidate(latex, kind))
        prose.append(_SENTINEL)
    return math, "".join(prose)


def _plain(number: str) -> str:
    """A matched numerator or denominator without thousands separators or parentheses."""
    return re.sub(r"[\s,()]", "", number)


def _prose_numbers(chunk: str) -> list[Candidate]:
    """Every number in a prose chunk as an unsigned magnitude. A digit no number or ordinal
    covers (``12cm``, ``1.2e1``, ``3/0.25``) is unreadable and raises ``MalformedMath``."""
    found: list[Candidate] = []
    covered = [m.span() for m in _ORDINAL.finditer(chunk)]
    for m in _PROSE_NUMBER.finditer(chunk):
        covered.append(m.span())
        num = _plain(m["n1"] or m["n2"] or m["n3"])
        den = m["d1"] or m["d2"] or m["d3"]
        found.append(Candidate(f"{num}/{_plain(den)}" if den else num, "prose_number"))
    # The spans never overlap: the digit run lies in the last one starting at or before it.
    covered.sort()
    starts = [lo for lo, _ in covered]
    for d in _DIGITS.finditer(chunk):
        k = bisect.bisect_right(starts, d.start()) - 1
        if k < 0 or covered[k][1] < d.end():
            raise MalformedMath("a number glued to other text")
    return found


def _prose_candidates(prose: str, numbers: bool, terms: bool) -> list[Candidate]:
    """The right side of each prose ``=`` (to the next ``=``, math span or line end), then
    decimal literals in the remaining prose; with ``numbers`` every number instead, and with
    ``terms`` also coefficient-letter terms such as ``2x``. The remaining prose keeps its line
    breaks, so a number may continue on the next line (``12 /`` then ``121``)."""
    rhs: list[Candidate] = []
    lines: list[str] = []
    for line in prose.split("\n"):
        head, *sides = line.split("=")
        rest = [head]
        for side in sides:
            piece, _, after = side.partition(_SENTINEL)
            latex = _clean(piece)
            if latex:
                rhs.append(Candidate(latex, "equation_rhs"))
            rest.append(after)
        lines.append(_CHUNK_BREAK.join(rest))
    remaining = "\n".join(lines).replace(_SENTINEL, " ")
    if numbers:
        found = _prose_numbers(remaining)
    else:
        found = [Candidate(m.group(), "decimal") for m in _PROSE_DECIMAL.finditer(remaining)]
    if terms:
        found += [Candidate(m.group(), "prose_term") for m in _PROSE_TERM.finditer(remaining)]
    return rhs + found


def _dedupe(candidates: list[Candidate], limit: int) -> list[Candidate]:
    """First occurrence of each parsed tree (or, unparsed, each LaTeX string); stops once
    there are more than ``limit``. Each distinct LaTeX string is parsed once."""
    keys: dict[str, str] = {}
    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in candidates:
        key = keys.get(candidate.latex)
        if key is None:
            parsed = parse_latex(candidate.latex)
            key = (
                "latex:" + candidate.latex
                if isinstance(parsed, ParseRejected)
                else json.dumps(parsed.tree, sort_keys=True)
            )
            keys[candidate.latex] = key
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
            if len(unique) > limit:
                break
    return unique


def extract_candidates(
    text: str, limits: GuardLimits, *, numbers: bool = False, terms: bool = False
) -> list[Candidate] | None:
    """Every distinct math candidate in ``text``, in order: delimited math, prose equations,
    then prose decimals, or every prose number when ``numbers`` (numeric problems), plus
    ``2x``-style prose terms when ``terms`` (expression problems).

    Duplicates (same parsed tree) are dropped first; returns None when more than
    ``limits.max_candidates`` remain. Raises ``MalformedMath`` for an unbalanced delimiter,
    LaTeX (a command, ``^`` or ``_``) left in the prose, or, with ``numbers``, a digit run
    glued to other text.
    """
    math, prose = _split_math(text)
    if _PROSE_LATEX.search(prose):
        raise MalformedMath("LaTeX outside a math span")
    found = _dedupe(math + _prose_candidates(prose, numbers, terms), limits.max_candidates)
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

_DECIMAL_2 = re.compile(r"(?<!\d)\d*\.\d{2,}")  # starts only at a run's first digit


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
# Between "option"/"choice" and the letter: spaces, ":", "#" and dashes, repeated (R14).
_NOUN_SEP = r"[\s:#–—-]*"


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
        # After the nouns "option(s)"/"choice(s)" the letter is always the choice (R11, R14).
        re.compile(rf"\b(?:option|choice)s?{_NOUN_SEP}{letter}\b", flags),
        re.compile(rf"\({letter}\)", flags),
        re.compile(rf"^[ \t]*\(?{letter}[).]", flags),
        re.compile(rf"\b{_ORDINALS[index]}\s+{_NOUN}", flags),
        re.compile(rf"\b{_NUMBERED[index]}\b", flags),
        re.compile(rf"\b{_NOUN}\s*(?:#\s*)?{index + 1}\b", flags),
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


MAX_FOREIGN_LETTERS = 3


def _substitute(tree: JsonValue, values: dict[str, JsonValue]) -> JsonValue:
    """``tree`` with each symbol in ``values`` replaced by its value (heads untouched)."""
    if isinstance(tree, str):
        return values.get(tree, tree)
    if isinstance(tree, list) and tree:
        return [tree[0], *(_substitute(operand, values) for operand in tree[1:])]
    return tree


def _variants(
    tree: JsonValue, letters: frozenset[str], variable: str, *, ones: bool = False
) -> list[JsonValue]:
    """All letters -> variable, all -> 0, then each letter alone -> variable with the others
    -> 0 (``2t + C``: t -> x, C -> 0); with ``ones`` (numeric problems) also all -> 1, so a
    unit (``12 m``) reads as its number. Distinct trees only."""
    ordered = sorted(letters)
    assignments: list[dict[str, JsonValue]] = [
        dict.fromkeys(ordered, variable),
        dict.fromkeys(ordered, 0),
    ]
    for letter in ordered:
        assignments.append({other: (variable if other == letter else 0) for other in ordered})
    if ones:
        assignments.append(dict.fromkeys(ordered, 1))
    variants: list[JsonValue] = []
    for values in assignments:
        variant = _substitute(tree, values)
        if variant not in variants:
            variants.append(variant)
    return variants


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
        numeric = isinstance(answer, NumericAnswer)
        try:
            candidates = extract_candidates(
                text,
                self._limits,
                numbers=numeric,
                terms=isinstance(answer, ExpressionAnswer),
            )
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
                    status, reason = self._check_foreign(parsed, reference, deadline, ids, numeric)
                    if status is LeakStatus.NO_MATCH:
                        foreign += 1
                else:
                    status, reason = self._check_tree(parsed.tree, reference, deadline, ids)
                    if status is LeakStatus.NO_MATCH and candidate.origin == "prose_number":
                        # Prose numbers are unsigned magnitudes: check the other sign too.
                        flipped: JsonValue = ["Negate", parsed.tree]
                        status, reason = self._check_tree(flipped, reference, deadline, ids)
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
        numeric: bool,
    ) -> tuple[LeakStatus, str]:
        """A tree with foreign names is never checked as written. When every foreign name is a
        single-letter symbol (at most three), its substitution variants are checked
        (``_variants``); it is a no match only when every variant is one. The first leak or
        unchecked variant (busy, error, timeout, deadline) decides. More than three letters is
        unchecked."""
        letters = _substitutable(parsed)
        if letters is None:
            return LeakStatus.NO_MATCH, ""
        if len(letters) > MAX_FOREIGN_LETTERS:
            return LeakStatus.UNCHECKED, "too_many_foreign"
        variants = _variants(parsed.tree, letters, reference.variable, ones=numeric)
        for tree in variants:
            status, reason = self._check_tree(tree, reference, deadline, ids)
            if status is not LeakStatus.NO_MATCH:
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
