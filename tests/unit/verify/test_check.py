from __future__ import annotations

import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import mpmath
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sympy import Rational

from mathtutor import __version__
from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import (
    ChoiceAnswer,
    Decimals,
    Domain,
    ExpressionAnswer,
    NumericAnswer,
)
from mathtutor.domain import AnswerKind, FormatIssueCode, Method, VerdictReason, VerdictStatus
from mathtutor.verify import check as check_module
from mathtutor.verify.check import VERIFIER_VERSION, check
from mathtutor.verify.numeric import round_matches
from mathtutor.verify.types import (
    CheckRequest,
    CheckResult,
    FormatIssue,
    SubmittedAnswer,
    Verdict,
)

ROOT = Path(__file__).resolve().parents[3]
SEED = load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
BY_ID = {p.id: p for p in SEED}

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
NOT_PROVEN = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.NOT_PROVEN, Method.NONE)
DOMAIN_UNPROVEN = Verdict(
    VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.DOMAIN_UNPROVEN, Method.DOMAIN
)
INTERNAL_ERROR = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.INTERNAL_ERROR, Method.NONE)

ROUNDED_MATCH = Verdict(VerdictStatus.CORRECT, VerdictReason.ROUNDED_MATCH, Method.ROUNDING)
ROUNDED_MISMATCH = Verdict(VerdictStatus.INCORRECT, VerdictReason.ROUNDED_MISMATCH, Method.ROUNDING)


def decimals_spec(tree: Any, n: int) -> NumericAnswer:
    return NumericAnswer(kind="numeric", latex="", mathjson=tree, precision=Decimals(decimals=n))


def expression_spec(tree: Any, domain: Domain | None = None, strict: bool = False) -> Any:
    return ExpressionAnswer(
        kind="expression",
        latex="",
        mathjson=tree,
        domain=domain or Domain(),
        strict_domain=strict,
    )


def submit(spec: Any, tree: Any, latex: str = "x") -> CheckRequest:
    return CheckRequest(spec, SubmittedAnswer(spec.kind, tree, latex, None))


def choice_req(choice: str | None, correct: str) -> CheckRequest:
    spec = ChoiceAnswer(
        kind="choice",
        choices=[
            {"id": "a", "latex": "1", "mathjson": 1},
            {"id": "b", "latex": "2", "mathjson": 2},
        ],
        correct=correct,
    )
    return CheckRequest(spec, SubmittedAnswer(AnswerKind.CHOICE, None, "", choice))


def outcome(req: CheckRequest) -> Verdict | FormatIssue:
    result = check(req)
    assert isinstance(result, CheckResult)
    assert result.verifier_version == VERIFIER_VERSION
    return result.outcome


# -- choice ----------------------------------------------------------------------------------


def test_check_choice() -> None:
    assert outcome(choice_req("b", correct="b")) == Verdict(
        VerdictStatus.CORRECT, VerdictReason.CHOICE_MATCH, Method.EXACT
    )
    assert outcome(choice_req("a", correct="b")) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.CHOICE_MISMATCH, Method.EXACT
    )
    assert outcome(choice_req(None, correct="b")) == FormatIssue(FormatIssueCode.EMPTY)


def test_kind_mismatch_raises() -> None:
    spec = expression_spec("x")
    req = CheckRequest(spec, SubmittedAnswer(AnswerKind.NUMERIC, "x", "x", None))
    with pytest.raises(ValueError):
        check(req)


# -- numeric ---------------------------------------------------------------------------------


def test_check_numeric_decimal() -> None:
    spec = BY_ID["openstax-c1-3.6-253"].answer
    assert outcome(submit(spec, {"num": "-0.583"}, "-0.583")) == Verdict(
        VerdictStatus.CORRECT, VerdictReason.ROUNDED_MATCH, Method.ROUNDING
    )
    assert outcome(submit(spec, {"num": "-0.58"}, "-0.58")) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.ROUNDED_MISMATCH, Method.ROUNDING
    )


RATIONAL_253 = Rational(-200, 343)


@pytest.mark.parametrize(
    "tree,verdict",
    [
        # Compute Engine raw form sends every negative decimal as Negate of a decimal.
        (["Negate", {"num": "0.583"}], ROUNDED_MATCH),
        (["Negate", {"num": "0.58"}], ROUNDED_MISMATCH),
        (["Delimiter", ["Negate", {"num": "0.583"}]], ROUNDED_MATCH),  # (-0.583)
        (["Negate", ["Delimiter", {"num": "0.583"}]], ROUNDED_MATCH),  # -(0.583)
        (["Delimiter", ["Delimiter", ["Negate", {"num": "0.5831"}]]], ROUNDED_MATCH),
    ],
)
def test_check_numeric_negative_decimal_shapes(tree: Any, verdict: Verdict) -> None:
    spec = BY_ID["openstax-c1-3.6-253"].answer
    assert outcome(submit(spec, tree, "-0.583")) == verdict


def test_check_numeric_parenthesised_decimal() -> None:
    spec = decimals_spec("Pi", 2)
    assert outcome(submit(spec, ["Delimiter", {"num": "3.14"}], "(3.14)")) == ROUNDED_MATCH


@pytest.mark.parametrize(
    "tree",
    [
        ["Negate", ["Negate", {"num": "0.583"}]],  # double negation: not a decimal literal
        ["Negate", {"num": "-0.583"}],  # sign already in the literal
        ["Delimiter", {"num": "0.583"}, {"num": "1"}],  # Delimiter with two arguments
    ],
)
def test_check_numeric_other_shapes_are_graded_exactly(tree: Any) -> None:
    spec = BY_ID["openstax-c1-3.6-253"].answer
    result = outcome(submit(spec, tree, "x"))
    assert isinstance(result, FormatIssue) or result.status != VerdictStatus.CORRECT


def test_check_numeric_exact_symbolic() -> None:
    spec = BY_ID["openstax-c1-3.6-253"].answer
    exact = ["Divide", -200, 343]
    assert outcome(submit(spec, exact, "\\frac{-200}{343}")) == CORRECT
    wrong = ["Divide", -200, 49]
    assert outcome(submit(spec, wrong, "\\frac{-200}{49}")) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION
    )


def test_check_numeric_decimal_inside_a_tree_is_exact() -> None:
    spec = NumericAnswer(
        kind="numeric", latex="", mathjson=["Divide", 1, 4], precision=Decimals(decimals=2)
    )
    assert outcome(submit(spec, ["Divide", {"num": "0.5"}, 2], "0.5/2")) == CORRECT


@pytest.mark.parametrize(
    "tree,n,student,verdict",
    [
        (["Exp", 2], 3, "7.389", ROUNDED_MATCH),  # e^2 = 7.38905...
        (["Exp", 2], 3, "7.388", ROUNDED_MISMATCH),
        (["Power", "e", 2], 3, "7.389", ROUNDED_MATCH),
        (["Divide", "Pi", 4], 2, "0.79", ROUNDED_MATCH),  # pi/4 = 0.785398...
        (["Divide", "Pi", 4], 2, "0.78", ROUNDED_MISMATCH),
        (["Ln", 3], 4, "1.0986", ROUNDED_MATCH),  # ln 3 = 1.098612...
        (["Ln", 3], 4, "1.0987", ROUNDED_MISMATCH),
        (["Sqrt", 2], 0, "1", ROUNDED_MATCH),
        ("Pi", 2, "3.14", ROUNDED_MATCH),
    ],
)
def test_check_numeric_irrational_certified_rounding(
    tree: Any, n: int, student: str, verdict: Verdict
) -> None:
    assert outcome(submit(decimals_spec(tree, n), {"num": student}, student)) == verdict


def test_check_numeric_straddling_enclosure_abstains(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def straddle(expr: Any, var: Any, point: Any, dps: int = 60) -> Any:
        calls.append(dps)
        return (mpmath.mpf("7.38849"), mpmath.mpf("7.38851"))  # meets the 7.3885 boundary

    monkeypatch.setattr(check_module, "enclose", straddle)
    assert outcome(submit(decimals_spec(["Exp", 2], 3), {"num": "7.389"}, "7.389")) == NOT_PROVEN
    assert calls == [60, 120, 240]


def test_check_numeric_unenclosable_abstains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_module, "enclose", lambda *args, **kwargs: None)
    assert outcome(submit(decimals_spec(["Exp", 2], 3), {"num": "7.389"}, "7.389")) == NOT_PROVEN


def test_check_numeric_non_constant_expected_is_internal_error() -> None:
    assert outcome(submit(decimals_spec("x", 2), {"num": "1.5"}, "1.5")) == INTERNAL_ERROR


# -- expression ------------------------------------------------------------------------------


_PARENTHESIZED_SEED_LATEX = {"openstax-c1-3.5-181": r"(1-\sin(x))^2-(x+\cos(x))\cos(x)"}


@pytest.mark.parametrize("problem", SEED, ids=[p.id for p in SEED])
def test_check_expression_seed_answers(problem: Any) -> None:
    spec = problem.answer
    if spec.kind == "choice":
        req = CheckRequest(spec, SubmittedAnswer(AnswerKind.CHOICE, None, "", spec.correct))
        assert outcome(req).status == VerdictStatus.CORRECT
    else:
        # R22 rejects bare-function LaTeX; seed LaTeX is parenthesized in task 3 (then drop this).
        tex = _PARENTHESIZED_SEED_LATEX.get(problem.id, spec.latex)
        assert outcome(submit(spec, spec.mathjson, tex)) == CORRECT


def test_check_gap_certified() -> None:
    spec = expression_spec("x")
    assert outcome(submit(spec, ["Power", ["Sqrt", "x"], 2])) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.UNDEFINED_ON_DOMAIN, Method.DOMAIN
    )


def test_check_gap_uncertified_abstains(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_module, "refute", lambda *args, **kwargs: None)
    spec = expression_spec("x")
    assert outcome(submit(spec, ["Power", ["Sqrt", "x"], 2])) == DOMAIN_UNPROVEN


def test_check_refutation() -> None:
    spec = expression_spec(["Multiply", 2, "x"])
    assert outcome(submit(spec, ["Power", "x", 2])) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION
    )
    ln_spec = expression_spec(
        ["Ln", ["Power", "x", 2]],
        Domain(intervals=[("-inf", "0", "open", "open"), ("0", "inf", "open", "open")]),
    )
    assert outcome(submit(ln_spec, ["Multiply", 2, ["Ln", "x"]])) == Verdict(
        VerdictStatus.INCORRECT, VerdictReason.STUDENT_UNDEFINED, Method.REFUTATION
    )


def test_check_removable_hole_is_correct() -> None:
    spec = expression_spec(["Add", "x", 1])
    hole = ["Divide", ["Subtract", ["Power", "x", 2], 1], ["Subtract", "x", 1]]
    assert outcome(submit(spec, hole)) == CORRECT


def test_check_unproven_abstains() -> None:
    # x + 10^-70 differs from x below 60 digits on (1, 2): no proof and no certified point.
    spec = expression_spec("x", Domain(intervals=[("1", "2", "open", "open")]))
    assert outcome(submit(spec, ["Add", "x", ["Power", 10, -70]])) == NOT_PROVEN


def test_check_timeout() -> None:
    spec = expression_spec(["Multiply", 2, "x"])
    result = check(submit(spec, ["Add", "x", "x"]), deadline_s=0.0)
    assert result.outcome == Verdict(
        VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.TIMEOUT, Method.NONE
    )


def test_check_expected_rejected_is_internal_error(caplog: pytest.LogCaptureFixture) -> None:
    spec = expression_spec(["Foo", "x"])
    assert outcome(submit(spec, "x")) == INTERNAL_ERROR
    assert "expected answer" in caplog.text


@pytest.mark.parametrize(
    "tree,latex,code",
    [
        (None, "", FormatIssueCode.EMPTY),
        ("Nothing", "", FormatIssueCode.EMPTY),
        (["Add", "x", ["Error", "'missing'"]], "x+", FormatIssueCode.INCOMPLETE),
        ("x", "x^{}", FormatIssueCode.INCOMPLETE),
        (["Add", "x", 10**40], "x", FormatIssueCode.INPUT_TOO_LARGE),
        (["Add", *(["x"] * 250)], "x", FormatIssueCode.INPUT_TOO_LARGE),
        (["Foo", "x"], "x", FormatIssueCode.UNSUPPORTED_NOTATION),
        (["Power", "x", 5000], "x", FormatIssueCode.INPUT_TOO_LARGE),
        ("y", "y", FormatIssueCode.UNSUPPORTED_NOTATION),
    ],
)
def test_check_format_issue_passthrough(tree: Any, latex: str, code: FormatIssueCode) -> None:
    result = outcome(submit(expression_spec("x"), tree, latex))
    assert isinstance(result, FormatIssue)
    assert result.code == code


def test_check_format_issue_keeps_suggestion() -> None:
    tree = ["InvisibleOperator", "e", ["Delimiter", ["Add", "x", 1]]]
    result = outcome(submit(expression_spec("x"), tree, "e(x+1)"))
    assert isinstance(result, FormatIssue)
    assert result.code == FormatIssueCode.UNSUPPORTED_NOTATION
    assert "Did you mean e·(...)?" in result.detail


def test_check_exact_required() -> None:
    spec = NumericAnswer(kind="numeric", latex="", mathjson=["Divide", 1, 4], precision="exact")
    assert outcome(submit(spec, {"num": "0.25"}, "0.25")) == FormatIssue(
        FormatIssueCode.EXACT_REQUIRED
    )


def test_verifier_version() -> None:
    assert VERIFIER_VERSION.startswith(f"{__version__}+")


# -- robustness ------------------------------------------------------------------------------

_HEADS = ["Add", "Subtract", "Multiply", "Divide", "Power", "Sqrt", "Root", "Negate", "Sin"]
_HEADS += ["Cos", "Tan", "Ln", "Log", "Exp", "Abs", "Delimiter", "InvisibleOperator", "Foo"]
_LEAVES = st.one_of(
    st.integers(min_value=-(10**35), max_value=10**35),
    st.sampled_from(["x", "Pi", "e", "y", "Nothing", "ExponentialE"]),
    st.builds(lambda s: {"num": s}, st.sampled_from(["0.5", "-2.75", "1e-40", "abc", "3"])),
    st.builds(lambda s: ["Negate", {"num": s}], st.sampled_from(["0.583", "-0.5", "1.0"])),
    st.none(),
    st.booleans(),
)
_TREES = st.recursive(
    _LEAVES,
    lambda kids: st.one_of(
        st.builds(lambda h, a: [h, *a], st.sampled_from(_HEADS), st.lists(kids, max_size=3)),
        st.lists(kids, max_size=3),
        st.dictionaries(st.sampled_from(["num", "x"]), kids, max_size=2),
    ),
    max_leaves=12,
)


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(tree=_TREES, latex=st.sampled_from(["x", "", "x^{}", "\\placeholder{}"]))
def test_check_never_raises(tree: Any, latex: str) -> None:
    for problem in ("openstax-c1-3.6-221", "openstax-c1-3.6-253"):
        spec = BY_ID[problem].answer
        result = check(CheckRequest(spec, SubmittedAnswer(spec.kind, tree, latex, None)), 0.5)
        assert isinstance(result, CheckResult)
        assert isinstance(result.outcome, Verdict | FormatIssue)


_DECIMAL_TEXT = st.decimals(
    min_value=Decimal("-2"), max_value=Decimal("2"), allow_nan=False, places=4
).map(str)


@settings(max_examples=80, deadline=None)
@given(text=_DECIMAL_TEXT, shape=st.sampled_from(["bare", "negate", "delimiter"]))
def test_check_decimal_rounding_property(text: str, shape: str) -> None:
    """Seed 253: correct exactly when the typed decimal rounds like -200/343 at 3 places."""
    value = Decimal(text)
    magnitude = str(abs(value))
    if shape == "bare":
        tree: Any = {"num": text}
    elif value < 0 or (value == 0 and text.startswith("-")):
        tree = ["Negate", {"num": magnitude}]
    else:
        tree = {"num": magnitude}
    if shape == "delimiter":
        tree = ["Delimiter", tree]
    spec = BY_ID["openstax-c1-3.6-253"].answer
    result = check(CheckRequest(spec, SubmittedAnswer(spec.kind, tree, text, None)), 2.0)
    expected = ROUNDED_MATCH if round_matches(RATIONAL_253, value, 3) else ROUNDED_MISMATCH
    assert result.outcome == expected


def test_check_gap_without_point_after_deadline_is_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_none(interval: Any) -> None:
        time.sleep(1.1)  # the budget runs out while looking for a point

    monkeypatch.setattr(check_module, "rational_inside", slow_none)
    result = check(submit(expression_spec("x"), ["Power", ["Sqrt", "x"], 2]), deadline_s=1.0)
    assert result.outcome == Verdict(
        VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.TIMEOUT, Method.NONE
    )


def test_computed_exponent_log2_8_is_cubed_on_all_reals() -> None:
    # dev case d-log2-01: x^(log_2 8) = x^3 for every real x, negative x included.
    spec = expression_spec(["Power", "x", 3])
    assert outcome(submit(spec, ["Power", "x", ["Log", 8, 2]])) == CORRECT


def test_unprovable_near_rational_exponent_abstains() -> None:
    # cos(2pi/7) + cos(4pi/7) + cos(6pi/7) = -1/2 (no strategy proves it), so the exponent
    # below is exactly 1/3 and x^(1/3) is real for negative x: abstain, never reject.
    seventh = ["Divide", "Pi", 7]
    minus_half: Any = [
        "Add",
        *(["Cos", ["Multiply", k, seventh]] for k in (2, 4, 6)),
    ]
    third = ["Multiply", ["Rational", -2, 3], minus_half]
    spec = expression_spec(["Root", "x", 3])
    result = outcome(submit(spec, ["Power", "x", third]))
    assert isinstance(result, Verdict) and result.status == VerdictStatus.UNABLE_TO_VERIFY


# -- R23: restrictions decided on their inner argument -------------------------------------------


def _open(lo: str, hi: str) -> Domain:
    return Domain(intervals=[(lo, hi, "open", "open")])


def test_sin_over_cos_is_tan_on_minus_one_one() -> None:  # d-tan-01
    spec = expression_spec(["Tan", "x"], _open("-1", "1"))
    assert outcome(submit(spec, ["Divide", ["Sin", "x"], ["Cos", "x"]])) == CORRECT


def test_one_over_sin_is_csc() -> None:  # d-csc-02
    spec = expression_spec(["Csc", "x"], _open("1/2", "3"))
    assert outcome(submit(spec, ["Divide", 1, ["Sin", "x"]])) == CORRECT


def test_cot_third_from_cos_over_sin() -> None:  # d-cot-01
    spec = expression_spec(["Divide", ["Cot", ["Divide", "x", 3]], 3], _open("0", "9"))
    third = ["Divide", "x", 3]
    sub = ["Divide", ["Cos", third], ["Multiply", 3, ["Sin", third]]]
    assert outcome(submit(spec, sub)) == CORRECT


def test_ln_exp_is_x() -> None:  # d-explog-03
    spec = expression_spec("x")
    assert outcome(submit(spec, ["Ln", ["Exp", "x"]])) == CORRECT


def test_two_ln_abs_is_ln_square() -> None:  # d-lnsq-02
    spec = expression_spec(["Ln", ["Power", "x", 2]], Domain(exclude=["0"]))
    assert outcome(submit(spec, ["Multiply", 2, ["Ln", ["Abs", "x"]]])) == CORRECT


def test_cot_irrational_removable_hole_is_proven() -> None:  # d-cot-03
    third = ["Divide", "x", 3]
    spec = expression_spec(["Divide", ["Cot", third], 3], _open("0", "9"))
    # the hole at 3pi/2 is removable: both one-sided limits are 0, the reference value there
    assert outcome(submit(spec, ["Divide", 1, ["Multiply", 3, ["Tan", third]]])) == CORRECT


def test_strict_trig_of_exp_and_abs_is_not_proven_correct() -> None:
    # tan(e^x) is undefined at ln(pi/2) in (0, 1); cot(|x|) at pi in (1, 4).
    exp_spec = expression_spec(["Sin", ["Exp", "x"]], _open("0", "1"), strict=True)
    exp_sub = ["Multiply", ["Tan", ["Exp", "x"]], ["Cos", ["Exp", "x"]]]
    abs_spec = expression_spec(["Cos", ["Abs", "x"]], _open("1", "4"), strict=True)
    abs_sub = ["Multiply", ["Cot", ["Abs", "x"]], ["Sin", ["Abs", "x"]]]
    for spec, sub in ((exp_spec, exp_sub), (abs_spec, abs_sub)):
        result = outcome(submit(spec, sub))
        assert isinstance(result, Verdict) and result.status != VerdictStatus.CORRECT
