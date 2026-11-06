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
    assert len(pool.requests) == 2  # u -> x and u -> 0 (R8)


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
    for text in [
        "Pick option (a).",
        "I'd go with Choice A",
        "the answer a; done",
        "Try (A) first.",
    ]:
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


# -- fix round 1: under-block paths (rulings R6-R9, M-1) -------------------------------------


class TreePool(FakePool):
    """CORRECT for exactly the given LaTeX forms (compared as parsed trees), else COUNTER."""

    def __init__(self, *leaking: str) -> None:
        super().__init__()
        self.leaking = [_mj(latex) for latex in leaking]

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        hit = req.answer.mathjson in self.leaking
        return CheckResult(CORRECT if hit else COUNTER, "test")


TWO_X = ExpressionAnswer(kind="expression", latex="2x", mathjson=_mj("2x"))  # type: ignore[arg-type]
TWELVE = NumericAnswer(
    kind="numeric",
    latex="12",
    mathjson=12,
    precision="exact",
)


@pytest.mark.parametrize(
    "text",
    [
        "The answer is a.",
        "Answer: a",
        "Pick A",
        "Option **a** fits.",
        "option 'a' fits",
        "It is choice-a",
        "the answer would be (a)",
        "a) is right",
        "  (a) is right",
        "Select a",
        "Pick A\nthen check it",
        "Pick a, it fits",
        "The answer is ( a ) here",
        "Option “a” fits",
        "The first option is right.",
        "Go with the first choice",
        "the 1st one",
        "Option 1 works",
    ],
)
def test_choice_phrasings_block(text: str) -> None:
    result, pool = _check(text, answer=CHOICE)
    assert (result.decision, result.reason) == ("block", "choice_reference"), text
    assert pool.requests == []


@pytest.mark.parametrize(
    "text",
    [
        "Now consider (b).",
        "First, differentiate.",
        "The second option is wrong.",
        "Pick a test point",
        "The answer is a product of two functions",
        "Choose a value of x",
        "Select a point, then",  # "a point": the article, not the choice
    ],
)
def test_choice_wrong_letter_and_plain_prose_pass(text: str) -> None:
    result, _ = _check(text, answer=CHOICE, pool=TreePool())
    assert result.decision != "block", text


@pytest.mark.parametrize("text", ["The answer is 12.", "It equals -12", "So 24/2 here."])
def test_prose_numbers_block_on_numeric(text: str) -> None:
    result, _ = _check(text, answer=TWELVE, pool=TreePool("12", "24/2"))
    assert (result.decision, result.reason) == ("block", "leak"), text


def test_prose_numbers_extracted_only_for_numeric() -> None:
    # A signed number is kept as its magnitude; the sign flip is checked for every number.
    assert extract_candidates("Step 2 gives 12 and -3.5 or 1/4.", LIMITS, numbers=True) == [
        Candidate("2", "prose_number"),
        Candidate("12", "prose_number"),
        Candidate("3.5", "prose_number"),
        Candidate("1/4", "prose_number"),
    ]
    result, pool = _check("Step 2 gives 7.", answer=TWELVE, pool=TreePool("12"))
    assert (result.decision, result.reason) == ("pass", "checked")
    sent = [r.answer.mathjson for r in pool.requests]
    assert sent == [2, ["Negate", 2], 7, ["Negate", 7]]
    result, pool = _check("The answer is 12.", answer=EXPR, pool=TreePool("12"))
    assert result.decision == "no_detected_math" and pool.requests == []


def test_prose_numbers_count_toward_cap() -> None:
    text = " ".join(str(n) for n in range(1, 22))
    assert extract_candidates(text, LIMITS, numbers=True) is None
    result, _ = _check(text, answer=TWELVE)
    assert (result.decision, result.reason) == ("block", "too_many_candidates")


@pytest.mark.parametrize("text", ["Then $2t$.", "So $2x + C$."])
def test_foreign_letters_are_substituted(text: str) -> None:
    result, _ = _check(text, answer=TWO_X, pool=TreePool("2x", "2x + 0"))
    assert (result.decision, result.reason) == ("block", "leak"), text
    assert result.counts[LeakStatus.LEAK] == 1


def test_foreign_substitution_without_match_keeps_no_match() -> None:
    result, pool = _check("First $18u^2$.", pool=TreePool("126(7x-4)^2"))
    assert (result.decision, result.foreign) == ("pass", 1)
    assert result.counts[LeakStatus.NO_MATCH] == 1
    sent = [r.answer.mathjson for r in pool.requests]
    assert sent == [["Multiply", 18, ["Power", "x", 2]], ["Multiply", 18, ["Power", 0, 2]]]


def test_non_letter_foreign_is_checked() -> None:
    """Review C1-R2: applications, Greek, primes and d/dx are substituted and checked like
    single letters; none passes without a checker verdict."""
    result, pool = _check(r"Let $f(x)$ and $\frac{du}{dx}$.", answer=TWO_X, pool=TreePool("2x"))
    assert (result.decision, result.foreign) == ("pass", 2)
    assert pool.requests
    mixed, pool = _check("So $u + f(x)$.", answer=TWO_X, pool=TreePool("2x"))
    assert mixed.decision == "pass" and pool.requests


@pytest.mark.parametrize(
    "text", [r"So $2x + f(x)$.", r"So $2x + \theta$.", r"So $2x + y'$.", r"So $2x + x_1$."]
)
def test_answer_plus_foreign_atom_is_checked_with_atom_as_zero(text: str) -> None:
    result, _ = _check(text, answer=TWO_X, pool=TreePool("2x + 0"))
    assert (result.decision, result.reason) == ("block", "leak"), text


def test_identical_applications_share_one_atom() -> None:
    _, pool = _check(r"So $f(x) - f(x) + g(2x)$.", answer=TWO_X, pool=TreePool())
    first = pool.requests[0].answer.mathjson
    assert first == ["Add", ["Subtract", "x", "x"], "x"], first


def test_more_than_three_foreign_atoms_block() -> None:
    result, pool = _check(r"So $f(x) + \theta + y' + x_1$.", answer=TWO_X, pool=TreePool())
    assert (result.decision, result.reason) == ("block", "too_many_foreign")
    assert pool.requests == []


@pytest.mark.parametrize(
    "text", [r"\begin{equation}2x\end{equation}", "2x^2 here", r"\\(2x\\)", "x_1 is"]
)
def test_prose_latex_is_malformed(text: str) -> None:
    result, pool = _check(text)
    assert (result.decision, result.reason) == ("block", "malformed_math"), text
    assert pool.requests == []


def test_escaped_dollar_prose_passes() -> None:
    result, _ = _check(r"It costs \$5 to print $2x$.", pool=TreePool())
    assert result.decision == "pass"


def test_escaped_percent_amp_hash_prose_pass() -> None:
    result, _ = _check(r"About 5\% of R\&D, item \#3: $2x$.", pool=TreePool())
    assert result.decision == "pass"
    for text in [r"Use \textbf{this}", r"a \, b", "end \\"]:
        result, _ = _check(text)
        assert (result.decision, result.reason) == ("block", "malformed_math"), text


def test_bang_is_kept_inside_math() -> None:
    assert extract_candidates("Note $5!$ here", LIMITS) == [Candidate("5!", "inline")]
    result, _ = _check("Note $5!$ here", pool=TreePool("5"))
    assert (result.decision, result.reason) == ("block", "parse_rejected")
    assert extract_candidates("y' = 2x!", LIMITS) == [Candidate("2x", "equation_rhs")]


# -- fix round 3 (rulings R11-R13) -----------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Option A is correct",
        "Choice A works",
        "choice a is the one",
        "I'd select option a since",
        "Option #a fits",
        "choice#a fits",
    ],
)
def test_noun_then_letter_blocks(text: str) -> None:
    result, _ = _check(text, answer=CHOICE)
    assert (result.decision, result.reason) == ("block", "choice_reference"), text


@pytest.mark.parametrize(
    ("text", "magnitude"),
    [
        ("So 12 / 121 here", "12/121"),
        ("It is -200 / 343", "200/343"),
        ("It is 200÷343", "200/343"),
        ("It is (-200)/343", "200/343"),
        ("It is -(200/343)", "200/343"),
        ("It is −200/343", "200/343"),
    ],
)
def test_prose_fractions(text: str, magnitude: str) -> None:
    assert extract_candidates(text, LIMITS, numbers=True) == [Candidate(magnitude, "prose_number")]
    pool = TreePool()
    _check(text, answer=TWELVE, pool=pool)
    tree = _mj(magnitude)
    assert [r.answer.mathjson for r in pool.requests] == [tree, ["Negate", tree]]


def test_sign_flip_leak_blocks() -> None:
    pool = FakePool(COUNTER, CORRECT)
    result, _ = _check("It is 200/343.", answer=TWELVE, pool=pool)
    assert (result.decision, result.reason) == ("block", "leak")


@pytest.mark.parametrize("text", ["It is 12cm", "So 12x", "About 1.2e1", "Use 3/0.25", "12/121ths"])
def test_glued_numbers_are_malformed_on_numeric(text: str) -> None:
    result, pool = _check(text, answer=TWELVE)
    assert (result.decision, result.reason) == ("block", "malformed_math"), text
    assert pool.requests == []


def test_glued_numbers_ignored_off_numeric() -> None:
    result, _ = _check("It is 12cm long", answer=EXPR)
    assert result.decision == "no_detected_math"


def test_repeated_numbers_dedupe_before_cap() -> None:
    text = (
        "Start with 2 and 3. Multiply 2 by 3 to get 6. Add 2 to 6 to get 8. "
        "Now 8 minus 3 is 5, and 5 plus 2 is 7. Check: 7 minus 2 is 5, 5 plus 3 is 8, "
        "8 minus 2 is 6, 6 over 3 is 2, and 2 times 3 is 6 again. So 2, 3, 5, 6, 7 and 8."
    )
    found = extract_candidates(text, LIMITS, numbers=True)
    assert found is not None and len(found) == 6
    result, _ = _check(text, answer=TWELVE)
    assert result.decision == "pass"


def test_each_foreign_letter_tried_alone() -> None:
    pool = TreePool()
    result, _ = _check("So $2t + C$.", answer=TWO_X, pool=pool)
    assert (result.decision, result.foreign) == ("pass", 1)
    sent = [r.answer.mathjson for r in pool.requests]
    assert sorted(map(str, sent)) == sorted(
        map(
            str,
            [
                ["Add", ["Multiply", 2, "x"], "x"],  # all -> x
                ["Add", ["Multiply", 2, 0], 0],  # all -> 0
                ["Add", ["Multiply", 2, "x"], 0],  # t -> x, C -> 0
                ["Add", ["Multiply", 2, 0], "x"],  # C -> x, t -> 0
            ],
        )
    )
    # Only the t -> x, C -> 0 variant is the tree 2x + 0.
    leak, _ = _check("So $2t + C$.", answer=TWO_X, pool=TreePool("2x + 0"))
    assert (leak.decision, leak.reason) == ("block", "leak")


def test_more_than_three_foreign_letters_unchecked() -> None:
    result, pool = _check("Say $a + b + c + d$.", answer=TWO_X, pool=TreePool())
    assert (result.decision, result.reason) == ("block", "too_many_foreign")
    assert result.counts[LeakStatus.UNCHECKED] == 1 and pool.requests == []
    ok, _ = _check("Say $a + b + c$.", answer=TWO_X, pool=TreePool())
    assert ok.decision == "pass"


@pytest.mark.parametrize(
    "text",
    [
        "option" + " " * 20_000 + "1x",
        "answer" + " " * 20_000,
        "\n" * 20_000 + "z",
        "7" * 20_000,
        "1" * 20_000 + ".5",
        "pick" + "*" * 20_000,
        "option is is " * 1_500,
    ],
    ids=["spaces", "answer", "newlines", "digits", "decimal", "marks", "fillers"],
)
def test_rules_are_fast_on_20kb(text: str) -> None:
    import time

    from mathtutor.help.leak_guard import _rule_violation

    for answer in (CHOICE, ROUNDED_NUMERIC):
        started = time.perf_counter()
        _rule_violation(text, answer)
        assert time.perf_counter() - started < 0.1, text[:20]


@pytest.mark.parametrize(
    ("text", "decision"),
    [("The answer is 2x.", "block"), ("Answer: **2x**", "block"), ("multiply by 3x", "pass")],
)
def test_prose_terms_on_expression(text: str, decision: str) -> None:
    result, _ = _check(text, answer=TWO_X, pool=TreePool("2x"))
    assert result.decision == decision, text
    assert extract_candidates("by 3x and 4y.", LIMITS, terms=True) == [
        Candidate("3x", "prose_term"),
        Candidate("4y", "prose_term"),
    ]


# -- fix round 4 (ruling R14) ----------------------------------------------------------------


class BusyAfter(FakePool):
    """The first ``ok`` calls are COUNTER, every later one is ``then``."""

    def __init__(self, ok: int, then: Verdict | type[Exception]) -> None:
        super().__init__(*([COUNTER] * ok))
        self.then = then

    def submit(self, req: CheckRequest) -> CheckResult:
        if not self.script:
            self.script.append(self.then)
        return super().submit(req)


@pytest.mark.parametrize("text", ["So $2t$.", "So $2t + C$."])
@pytest.mark.parametrize(
    ("then", "reason"), [(VerifierBusy, "verifier_busy"), (TIMEOUT, "unverified")]
)
def test_unchecked_foreign_variant_blocks(
    text: str, then: Verdict | type[Exception], reason: str
) -> None:
    for ok in (0, 1):
        result, _ = _check(text, answer=TWO_X, pool=BusyAfter(ok, then))
        assert (result.decision, result.reason) == ("block", reason), (text, ok)
        assert result.counts[LeakStatus.UNCHECKED] == 1 and result.foreign == 0


@pytest.mark.parametrize("text", ["So $2t$.", "So $2t + C$."])
def test_all_timeout_foreign_variants_block(text: str) -> None:
    pool = FakePool()
    pool.default = TIMEOUT
    result, _ = _check(text, answer=TWO_X, pool=pool)
    assert (result.decision, result.reason) == ("block", "unverified")


@pytest.mark.parametrize("text", ["So $2t$.", "So $2t + C$."])
def test_deadline_crossed_mid_variants_blocks(text: str) -> None:
    clock = Clock(now=0.0)

    class Slow(FakePool):
        def submit(self, req: CheckRequest) -> CheckResult:
            clock.now += 2.0
            return super().submit(req)

    pool = Slow()
    result = LeakGuard(pool, LIMITS, clock).check(text, TWO_X, deadline=1.0)
    assert (result.decision, result.reason) == ("block", "deadline")
    assert len(pool.requests) == 1


class ExactPool(FakePool):
    """CORRECT for exactly the given trees, else COUNTER."""

    def __init__(self, *leaking: object) -> None:
        super().__init__()
        self.leaking = list(leaking)

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        return CheckResult(CORRECT if req.answer.mathjson in self.leaking else COUNTER, "test")


@pytest.mark.parametrize(
    ("text", "ones"),
    [
        ("x = 12cm", ["Multiply", 12, 1, 1]),
        ("The total = 12 m.", ["Multiply", 12, 1]),
        ("So $12 m$.", ["Multiply", 12, 1]),
        ("So $12m$.", ["Multiply", 12, 1]),
    ],
)
def test_numeric_foreign_letters_also_tried_as_one(text: str, ones: object) -> None:
    result, pool = _check(text, answer=TWELVE, pool=ExactPool(ones))
    assert (result.decision, result.reason) == ("block", "leak"), text
    # Expression problems keep the variable and 0 variants only.
    _, pool = _check("So $2t$.", answer=TWO_X, pool=ExactPool())
    assert [r.answer.mathjson for r in pool.requests] == [
        ["Multiply", 2, "x"],
        ["Multiply", 2, 0],
    ]


@pytest.mark.parametrize(
    "text",
    [
        "The correct choice: A because it fits",
        "Option-A is right",
        "the choice—A—is right",
        "choice ## A",
        "Options A and C",
        "the choice – a – fits",
    ],
)
def test_noun_separators_block(text: str) -> None:
    result, _ = _check(text, answer=CHOICE)
    assert (result.decision, result.reason) == ("block", "choice_reference"), text


def test_make_a_choice_passes() -> None:
    result, _ = _check("Make a choice and stick with it", answer=CHOICE, pool=TreePool())
    assert result.decision != "block"


@pytest.mark.parametrize("text", ["2 " * 5000, "(1 " * 6000], ids=["twos", "parens"])
def test_extraction_is_fast_on_repeats(text: str) -> None:
    import time

    for numbers in (True, False):
        started = time.perf_counter()
        extract_candidates(text, LIMITS, numbers=numbers)
        assert time.perf_counter() - started < 0.3, (text[:6], numbers)


def test_prose_fraction_across_line_break() -> None:
    found = extract_candidates("So 12 /\n121.", LIMITS, numbers=True)
    assert found == [Candidate("12/121", "prose_number")]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("It is 200/(343)", ["200/343"]),
        ("It is -200 / ( 343 )", ["200/343"]),
        ("About 1,200 here", ["1200"]),
        ("About 12,345,678 here", ["12345678"]),
        ("So 1/1,200 here", ["1/1200"]),
        ("Count 1, 2, 3 then", ["1", "2", "3"]),
        ("Count 1,2,3 then", ["1", "2", "3"]),
    ],
)
def test_prose_number_forms(text: str, expected: list[str]) -> None:
    found = extract_candidates(text, LIMITS, numbers=True)
    assert found == [Candidate(e, "prose_number") for e in expected], text


@pytest.mark.parametrize(
    "text", ["Take the 2nd derivative.", "The 1st step", "the 3rd and 4th terms", "the 12th"]
)
def test_ordinals_are_not_numbers(text: str) -> None:
    result, pool = _check(text, answer=TWELVE, pool=TreePool("12"))
    assert result.decision == "no_detected_math", text
    assert pool.requests == []


@pytest.mark.parametrize("text", ["12/121ths", "the 2nds", "x2nd 5", "2nd12"])
def test_ordinal_lookalikes_stay_malformed(text: str) -> None:
    result, _ = _check(text, answer=TWELVE)
    assert (result.decision, result.reason) == ("block", "malformed_math"), text


def test_clearance_after_the_deadline_is_unchecked() -> None:
    """Review C1-R5: a no-match verdict that returns after the deadline blocks."""
    clock = Clock()

    class LatePool(FakePool):
        def submit(self, req: CheckRequest) -> CheckResult:
            clock.now += 5.0
            return super().submit(req)

    result = _guard(LatePool(), clock).check("So $3u$.", TWO_X, clock() + 1.0)
    assert (result.decision, result.reason) == ("block", "deadline")
