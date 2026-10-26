"""Fail-closed leak guard: extraction, classification and decisions (C1 Task 3).

A ``FakePool`` returns scripted ``CheckResult``s; the real worker is exercised in
``tests/integration/test_guard_pool.py``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from mathtutor.content.schema import (
    Answer,
    ChoiceAnswer,
    Decimals,
    Domain,
    ExpressionAnswer,
    NumericAnswer,
)
from mathtutor.domain import AnswerKind, FormatIssueCode, Method, VerdictReason, VerdictStatus
from mathtutor.help.config import GuardLimits, load_help_config
from mathtutor.help.latex_parse import ParsedMath, parse_latex
from mathtutor.help.leak_guard import (
    Candidate,
    GuardResult,
    LeakGuard,
    LeakStatus,
    MalformedMath,
    classify,
    extract_candidates,
)
from mathtutor.verify.types import CheckRequest, CheckResult, FormatIssue, Verdict, VerifierBusy

ROOT = Path(__file__).parents[3]
CONFIG = ROOT / "src" / "mathtutor" / "help" / "help_config.json"
LIMITS: GuardLimits = load_help_config(CONFIG).guard

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
ROUNDED = Verdict(VerdictStatus.CORRECT, VerdictReason.ROUNDED_MATCH, Method.ROUNDING)
COUNTER = Verdict(VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION)
UNABLE = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.NOT_PROVEN, Method.NONE)
TIMEOUT = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.TIMEOUT, Method.NONE)


def _mj(latex: str) -> object:
    parsed = parse_latex(latex)
    assert isinstance(parsed, ParsedMath)
    return parsed.tree


EXPR = ExpressionAnswer(
    kind="expression",
    latex="126(7x-4)^2",
    mathjson=_mj("126(7x-4)^2"),  # type: ignore[arg-type]
    domain=Domain(intervals=[("0", "inf", "open", "open")]),
    strict_domain=True,
)
CHOICE = ChoiceAnswer.model_validate(
    {
        "kind": "choice",
        "correct": "a",
        "choices": [
            {"id": "a", "latex": r"2x\cos(x)-x^2\sin(x)", "mathjson": _mj(r"2x\cos(x)-x^2\sin(x)")},
            {"id": "b", "latex": r"2x\cos(x)+x^2\sin(x)", "mathjson": _mj(r"2x\cos(x)+x^2\sin(x)")},
        ],
    }
)
ROUNDED_NUMERIC = NumericAnswer(
    kind="numeric",
    latex=r"\frac{12}{121}",
    mathjson=_mj(r"\frac{12}{121}"),  # type: ignore[arg-type]
    precision=Decimals(decimals=2),
)
EXACT_NUMERIC = NumericAnswer(
    kind="numeric",
    latex=r"\frac{1}{2}",
    mathjson=_mj(r"\frac{1}{2}"),  # type: ignore[arg-type]
    precision="exact",
)


class FakePool:
    """Records requests; returns scripted outcomes, else ``default``."""

    def __init__(self, *script: Verdict | FormatIssue | type[Exception]) -> None:
        self.script = list(script)
        self.default: Verdict | FormatIssue = COUNTER
        self.requests: list[CheckRequest] = []

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        outcome = self.script.pop(0) if self.script else self.default
        if isinstance(outcome, type):
            raise outcome("scripted")
        return CheckResult(outcome, "test")


class Clock:
    def __init__(self, now: float = 100.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def _guard(pool: FakePool, clock: Clock | None = None) -> LeakGuard:
    return LeakGuard(pool, LIMITS, clock or Clock())


def _check(
    text: str, answer: Answer = EXPR, pool: FakePool | None = None, deadline: float = 1e9
) -> tuple[GuardResult, FakePool]:
    pool = pool or FakePool()
    return _guard(pool).check(text, answer, deadline), pool


# -- extraction ------------------------------------------------------------------------------


def test_extracts_all_delimiters() -> None:
    text = "Look: $a$ and $$b$$, then \\(c\\) or \\[d\\]. It costs \\$5.\ny' = e\nf'(x) = g.\n"
    found = extract_candidates(text, LIMITS)
    assert found == [
        Candidate("a", "inline"),
        Candidate("b", "display"),
        Candidate("c", "inline"),
        Candidate("d", "display"),
        Candidate("e", "equation_rhs"),
        Candidate("g", "equation_rhs"),
    ]


def test_math_equations_split_into_sides() -> None:
    found = extract_candidates("Since $y = x^2\\cos x$, we have", LIMITS)
    assert found == [Candidate("y", "inline"), Candidate("x^2\\cos x", "inline")]


def test_trailing_punctuation_is_stripped() -> None:
    assert extract_candidates("$x^2.$ and $2x,$", LIMITS) == [
        Candidate("x^2", "inline"),
        Candidate("2x", "inline"),
    ]


def test_prose_decimals_are_candidates() -> None:
    assert extract_candidates("It is about -0.5 here.", LIMITS) == [Candidate("-0.5", "decimal")]


def test_plain_prose_has_no_candidates() -> None:
    assert extract_candidates("Use the product rule on each factor.", LIMITS) == []


@pytest.mark.parametrize("text", ["$2x", "$$2x$", "\\(2x", "\\[2x", "2x\\)", "x\\] y"])
def test_unbalanced_delimiter_is_malformed(text: str) -> None:
    with pytest.raises(MalformedMath):
        extract_candidates(text, LIMITS)


def test_unbalanced_delimiter_blocks() -> None:
    result, pool = _check("$2x")
    assert (result.decision, result.reason) == ("block", "malformed_math")
    assert pool.requests == []


def test_more_than_20_blocks() -> None:
    text = " ".join(f"${n}x$" for n in range(1, 22))
    assert extract_candidates(text, LIMITS) is None
    result, pool = _check(text)
    assert (result.decision, result.reason) == ("block", "too_many_candidates")
    assert pool.requests == []
    exactly = " ".join(f"${n}x$" for n in range(1, 21))
    found = extract_candidates(exactly, LIMITS)
    assert found is not None and len(found) == 20


# -- classification --------------------------------------------------------------------------


def _result(outcome: Verdict | FormatIssue) -> CheckResult:
    return CheckResult(outcome, "test")


def _incorrect(reason: VerdictReason) -> Verdict:
    return Verdict(VerdictStatus.INCORRECT, reason, Method.REFUTATION)


def test_classify_table() -> None:
    assert classify(_result(CORRECT)) is LeakStatus.LEAK
    assert classify(_result(ROUNDED)) is LeakStatus.LEAK
    assert classify(_result(COUNTER)) is LeakStatus.NO_MATCH
    assert classify(_result(_incorrect(VerdictReason.STUDENT_UNDEFINED))) is LeakStatus.LEAK
    assert classify(_result(_incorrect(VerdictReason.UNDEFINED_ON_DOMAIN))) is LeakStatus.LEAK
    assert classify(_result(_incorrect(VerdictReason.POLE_ON_DOMAIN))) is LeakStatus.LEAK
    assert classify(_result(UNABLE)) is LeakStatus.UNCHECKED
    assert classify(_result(TIMEOUT)) is LeakStatus.UNCHECKED
    issue = FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, "x")
    assert classify(_result(issue)) is LeakStatus.UNCHECKED
    # Any other incorrect reason is not in the table: fail closed.
    assert classify(_result(_incorrect(VerdictReason.CHOICE_MISMATCH))) is LeakStatus.UNCHECKED

    busy, _ = _check("$2x$", pool=FakePool(VerifierBusy))
    assert (busy.decision, busy.reason) == ("block", "verifier_busy")
    assert busy.counts[LeakStatus.UNCHECKED] == 1

    rejected, pool = _check("$1/2x$")  # ambiguous: parse rejected
    assert (rejected.decision, rejected.reason) == ("block", "parse_rejected")
    assert rejected.counts[LeakStatus.UNCHECKED] == 1 and pool.requests == []

    foreign, pool = _check("$18u^2$")
    assert (foreign.decision, foreign.reason) == ("pass", "checked")
    assert foreign.counts[LeakStatus.NO_MATCH] == 1 and foreign.foreign == 1
    assert pool.requests == []


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [(CORRECT, "leak"), (UNABLE, "unverified"), (FormatIssue(FormatIssueCode.EMPTY), "unverified")],
)
def test_leak_or_unchecked_blocks(outcome: Verdict | FormatIssue, reason: str) -> None:
    result, _ = _check("$2x$", pool=FakePool(outcome))
    assert (result.decision, result.reason) == ("block", reason)


def test_pass_and_no_detected_math() -> None:
    result, pool = _check("$2x$ and $3x$")
    assert (result.decision, result.reason) == ("pass", "checked")
    assert result.counts == {LeakStatus.LEAK: 0, LeakStatus.NO_MATCH: 2, LeakStatus.UNCHECKED: 0}
    assert len(pool.requests) == 2
    empty, pool = _check("Think about the chain rule.")
    assert (empty.decision, empty.reason) == ("no_detected_math", "no_detected_math")
    assert pool.requests == []


def test_requests_carry_the_reference_and_no_model_latex() -> None:
    _, pool = _check("$x(2\\cos x - x\\sin x)$", answer=CHOICE)
    (req,) = pool.requests
    assert req.request_id == "guard:1"
    spec = req.answer_spec
    assert isinstance(spec, ExpressionAnswer)
    assert spec.mathjson == CHOICE.choices[0].mathjson and spec.strict_domain is False
    assert req.answer.kind is AnswerKind.EXPRESSION and req.answer.choice_id is None
    assert req.answer.latex == ""  # the guard's own parse is the reading
    assert req.answer.mathjson == _mj("x(2\\cos x - x\\sin x)")

    _, pool = _check("$2x$")
    spec = pool.requests[0].answer_spec
    assert isinstance(spec, ExpressionAnswer)
    assert spec.domain == EXPR.domain and spec.strict_domain is False

    _, pool = _check("$2x$", answer=EXACT_NUMERIC)
    spec = pool.requests[0].answer_spec
    assert isinstance(spec, ExpressionAnswer) and spec.mathjson == EXACT_NUMERIC.mathjson


def test_stops_at_first_leak_and_checks_duplicates_once() -> None:
    pool = FakePool(COUNTER, CORRECT)
    result, _ = _check("$2x$ then $2 x$ then $3x$ then $4x$", pool=pool)
    assert (result.decision, result.reason) == ("block", "leak")
    assert [r.request_id for r in pool.requests] == ["guard:1", "guard:2"]
    assert result.counts == {LeakStatus.LEAK: 1, LeakStatus.NO_MATCH: 1, LeakStatus.UNCHECKED: 0}


def test_deadline_spent_blocks() -> None:
    pool = FakePool()
    result = _guard(pool, Clock(now=50.0)).check("$2x$", EXPR, deadline=49.0)
    assert (result.decision, result.reason) == ("block", "deadline")
    assert result.counts[LeakStatus.UNCHECKED] == 1 and pool.requests == []


def test_guard_budget_caps_the_deadline() -> None:
    clock = Clock(now=0.0)

    class Slow(FakePool):
        def submit(self, req: CheckRequest) -> CheckResult:
            clock.now += LIMITS.budget_s
            return super().submit(req)

    pool = Slow()
    result = LeakGuard(pool, LIMITS, clock).check("$2x$ $3x$", EXPR, deadline=1e9)
    assert (result.decision, result.reason) == ("block", "deadline")
    assert len(pool.requests) == 1


# -- deterministic rules ---------------------------------------------------------------------


def test_choice_letter_blocks() -> None:
    for text in ["Pick option (a).", "I'd go with Choice A", "the answer a is", "Try (A) first."]:
        result, pool = _check(text, answer=CHOICE)
        assert (result.decision, result.reason) == ("block", "choice_reference"), text
        assert pool.requests == []
    for text in ["Now consider (b).", "the answer about choices"]:
        result, _ = _check(text, answer=CHOICE)
        assert result.decision != "block", text


def test_choice_formula_blocks() -> None:
    pool = FakePool(CORRECT)
    result, _ = _check("Is it $2x\\cos(x)-x^2\\sin(x)$?", answer=CHOICE, pool=pool)
    assert (result.decision, result.reason) == ("block", "leak")


def test_numeric_decimal_blocks() -> None:
    for text in ["It is about 0.54 here.", "So $y = 0.099$."]:
        result, pool = _check(text, answer=ROUNDED_NUMERIC)
        assert (result.decision, result.reason) == ("block", "decimal_literal"), text
        assert pool.requests == []
    result, _ = _check("Roughly 0.1 of the way.", answer=ROUNDED_NUMERIC)
    assert result.decision == "pass"


# -- the result carries no text --------------------------------------------------------------


def test_result_has_no_latex() -> None:
    names = {f.name for f in dataclasses.fields(GuardResult)}
    assert names == {"decision", "counts", "reason", "foreign"}
    secret = "x(2\\cos x - x\\sin x)"
    for pool in [FakePool(CORRECT), FakePool(UNABLE), FakePool()]:
        result, _ = _check(f"So ${secret}$ it is", answer=CHOICE, pool=pool)
        assert secret not in repr(result)
        assert set(result.counts) == set(LeakStatus)
        assert all(isinstance(v, int) for v in result.counts.values())
        assert isinstance(result.foreign, int)
        assert result.reason.replace("_", "").isalpha() and result.reason.islower()
