from __future__ import annotations

import time
from typing import Any

import pytest
import sympy
from sympy import Interval, Rational, oo, sqrt

from mathtutor.content.schema import Domain
from mathtutor.domain import VerdictReason
from mathtutor.verify.equivalence import Budget
from mathtutor.verify.refute import enclose, rational_inside, refute, sample_points
from mathtutor.verify.translate import (
    VARIABLE_ASSUMPTIONS,
    TranslateContext,
    Translated,
    translate,
)

x = sympy.Symbol("x", **VARIABLE_ASSUMPTIONS)

REALS = Domain()
NONZERO = Domain(intervals=[("-inf", "0", "open", "open"), ("0", "inf", "open", "open")])
CLOSED = Domain(intervals=[("-1", "2", "closed", "open"), ("5", "inf", "closed", "open")])
HOLED = Domain(intervals=[("0", "4", "open", "closed")], exclude=["1", "2"])

COUNTEREXAMPLE = VerdictReason.COUNTEREXAMPLE
STUDENT_UNDEFINED = VerdictReason.STUDENT_UNDEFINED


def T(tree: Any) -> Translated:
    result = translate(tree, TranslateContext())
    assert isinstance(result, Translated), result
    return result


def B() -> Budget:
    return Budget(time.monotonic() + 30)


def pts(domain: Domain) -> list[Any]:
    return sample_points(domain)


def cube_root(arg: Any) -> Any:
    return ["Power", arg, ["Divide", 1, 3]]


# -- refute ----------------------------------------------------------------------------------


def test_tiny_perturbation_refuted() -> None:
    s = T(["Add", "x", ["Divide", 1, 1000000000]])
    assert refute(s, T("x"), x, pts(REALS), B()) == COUNTEREXAMPLE


def test_ln_x2_vs_2lnx_student_undefined() -> None:
    s = T(["Multiply", 2, ["Ln", "x"]])
    e = T(["Ln", ["Power", "x", 2]])
    assert refute(s, e, x, pts(NONZERO), B()) == STUDENT_UNDEFINED


def test_sqrt_x2_vs_x_counterexample() -> None:
    s = T(["Sqrt", ["Power", "x", 2]])
    assert refute(s, T("x"), x, pts(REALS), B()) == COUNTEREXAMPLE


def test_equal_functions_not_refuted() -> None:
    s = T(["Sin", ["Multiply", 2, "x"]])
    e = T(["Multiply", 2, ["Sin", "x"], ["Cos", "x"]])
    assert refute(s, e, x, pts(REALS), B()) is None


def test_overlapping_enclosures_never_refute() -> None:
    # 10^-70 is below the 60-digit working precision near |x| >= 1: enclosures overlap.
    s = T(["Add", "x", ["Power", 10, -70]])
    points = [Rational(1), Rational(2), Rational(-7, 2), Rational(1000)]
    assert refute(s, T("x"), x, points, B()) is None


def test_removable_hole_is_not_a_witness() -> None:
    # (x^2-1)/(x-1) is undefined only at 1: a removable hole, correct unless strict.
    s = T(["Divide", ["Subtract", ["Power", "x", 2], 1], ["Subtract", "x", 1]])
    e = T(["Add", "x", 1])
    assert refute(s, e, x, [Rational(1), Rational(2), Rational(-3)], B()) is None


def test_isolated_trig_hole_is_not_a_witness() -> None:
    # tan x * cos x vs sin x: tan is undefined only at isolated points.
    s = T(["Multiply", ["Tan", "x"], ["Cos", "x"]])
    e = T(["Sin", "x"])
    assert refute(s, e, x, pts(REALS), B()) is None


def test_student_undefined_needs_expected_defined() -> None:
    # sqrt(x) vs sqrt(sqrt(x)) at -2: both undefined, so no witness there.
    s = T(["Sqrt", "x"])
    assert refute(s, T(["Sqrt", ["Sqrt", "x"]]), x, [Rational(-2)], B()) is None
    s2 = T(["Multiply", 2, ["Ln", "x"]])
    e2 = T(["Ln", ["Power", "x", 2]])
    assert refute(s2, e2, x, [Rational(-2)], B()) == STUDENT_UNDEFINED


def test_student_undefined_needs_a_whole_neighbourhood() -> None:
    # sqrt(x) is undefined only left of 0; at the point 0 itself it is defined.
    s = T(["Sqrt", ["Power", "x", 2]])
    e = T(["Abs", "x"])
    assert refute(T(["Power", ["Sqrt", "x"], 2]), T("x"), x, [Rational(0)], B()) is None
    assert refute(s, e, x, pts(REALS), B()) is None


def test_real_cube_root_refuted_at_negative_point() -> None:
    s = T(["Negate", cube_root("x")])
    assert refute(s, T(cube_root("x")), x, [Rational(-8)], B()) == COUNTEREXAMPLE


def test_real_cube_root_matches_root() -> None:
    s = T(cube_root("x"))
    e = T(["Root", "x", 3])
    assert refute(s, e, x, [Rational(-8), Rational(0), *pts(REALS)], B()) is None


def test_real_cube_root_is_not_principal_root() -> None:
    # x^(1/3) is the real root (R14): -2 at -8, so it differs from |x|^(1/3) there.
    s = T(cube_root("x"))
    e = T(cube_root(["Abs", "x"]))
    assert refute(s, e, x, [Rational(-8)], B()) == COUNTEREXAMPLE


def test_two_thirds_power_at_negative_point() -> None:
    # x^(2/3) = |x|^(2/3) is defined and positive for x < 0.
    s = T(["Power", "x", ["Divide", 2, 3]])
    e = T(["Power", ["Power", "x", 2], ["Divide", 1, 3]])
    assert refute(s, e, x, [Rational(-8), Rational(-1, 2)], B()) is None


def test_log_bases_are_enclosed() -> None:
    s = T(["Log", "x"])  # log base 10
    e = T(["Divide", ["Ln", "x"], ["Ln", 10]])
    assert refute(s, e, x, [Rational(3), Rational(1, 7)], B()) is None
    lb = T(["Lb", "x"])
    assert refute(lb, e, x, [Rational(3)], B()) == COUNTEREXAMPLE


def test_trig_functions_are_enclosed() -> None:
    s = T(["Add", ["Power", ["Sec", "x"], 2], 0])
    e = T(["Add", 1, ["Power", ["Tan", "x"], 2]])
    assert refute(s, e, x, pts(REALS), B()) is None
    cot = T(["Cot", "x"])
    assert refute(cot, T(["Divide", ["Cos", "x"], ["Sin", "x"]]), x, pts(REALS), B()) is None
    assert refute(cot, T(["Csc", "x"]), x, [Rational(1)], B()) == COUNTEREXAMPLE


def test_exp_and_symbolic_powers() -> None:
    s = T(["Power", "x", "x"])
    e = T(["Exp", ["Multiply", "x", ["Ln", "x"]]])
    assert refute(s, e, x, [Rational(1, 2), Rational(3)], B()) is None
    assert refute(T(["Exp", "x"]), T(["Power", "e", "x"]), x, pts(REALS), B()) is None
    assert refute(T(["Power", "x", "Pi"]), T("x"), x, [Rational(2)], B()) == COUNTEREXAMPLE


def test_evaluation_errors_skip_the_point() -> None:
    # 1/(x-1) at x = 1: both sides fail to evaluate there, so only x = 2 can refute.
    s = T(["Divide", 1, ["Subtract", "x", 1]])
    e = T(["Divide", 2, ["Subtract", "x", 1]])
    assert refute(s, e, x, [Rational(1)], B()) is None
    assert refute(s, e, x, [Rational(1), Rational(2)], B()) == COUNTEREXAMPLE


def test_huge_values_skip_the_point() -> None:
    s = T(["Exp", ["Exp", ["Exp", "x"]]])
    assert refute(s, T("x"), x, [Rational(1000)], B()) is None


def test_spent_budget_returns_none() -> None:
    s = T(["Add", "x", 1])
    assert refute(s, T("x"), x, pts(REALS), Budget(time.monotonic() - 1)) is None


# -- enclose ---------------------------------------------------------------------------------


def _exact(v: Any) -> Any:
    sign, man, exp, _ = v._mpf_
    return (-1) ** sign * Rational(man) * Rational(2) ** exp


@pytest.mark.parametrize(
    "tree,point,value",
    [
        (["Add", "x", ["Divide", 1, 3]], 0, Rational(1, 3)),
        (cube_root("x"), -8, -2),
        (["Abs", "x"], -3, 3),
        (["Sqrt", "x"], 2, sqrt(2)),
        (["Ln", "x"], 1, 0),
        (["Power", "x", 0], 0, 1),
    ],
)
def test_enclose_contains_exact_value(tree: Any, point: int, value: Any) -> None:
    box = enclose(T(tree).expr, x, Rational(point))
    assert box is not None
    lo, hi = (_exact(v) for v in box)
    assert lo <= value <= hi


@pytest.mark.parametrize(
    "tree,point",
    [
        (["Sqrt", "x"], -1),
        (["Ln", "x"], 0),
        (["Divide", 1, "x"], 0),
        (["Tan", "x"], None),  # tan at pi/2 is not a rational point; use a straddling box
        (["Power", "x", ["Divide", -1, 3]], 0),
    ],
)
def test_enclose_refuses_undefined(tree: Any, point: int | None) -> None:
    expr = T(tree).expr
    if point is None:
        expr = expr.xreplace({x: sympy.pi / 2 + x})
        point = 0
    assert enclose(expr, x, Rational(point)) is None


# -- sample_points ---------------------------------------------------------------------------


def _inside(domain: Domain, p: Any) -> bool:
    from mathtutor.verify.equivalence import to_sympy_set

    return to_sympy_set(domain).contains(p) is sympy.true


@pytest.mark.parametrize("domain", [REALS, NONZERO, CLOSED, HOLED])
def test_sample_points_deterministic_and_in_domain(domain: Domain) -> None:
    first = sample_points(domain)
    assert first == sample_points(domain)
    assert sample_points(domain, seed=1) != first
    assert len(first) >= 20
    assert len(set(first)) == len(first)
    assert all(isinstance(p, Rational) for p in first)
    assert all(_inside(domain, p) for p in first)


def test_sample_points_include_closed_ends_and_midpoints() -> None:
    points = sample_points(CLOSED)
    assert {Rational(-1), Rational(1, 2), Rational(5)} <= set(points)
    assert Rational(2) not in points  # open end
    holed = sample_points(HOLED)
    assert Rational(4) in holed
    assert Rational(1) not in holed and Rational(2) not in holed  # excluded points
    assert Rational(0) not in holed


def test_sample_points_n() -> None:
    assert len(sample_points(REALS, n=5)) >= 5
    assert len(sample_points(REALS, n=40)) >= 40


# -- rational_inside -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "interval",
    [
        Interval.open(-oo, 0),
        Interval.open(0, oo),
        Interval.open(-oo, oo),
        Interval.open(sqrt(2), oo),
        Interval.open(-oo, -sqrt(3)),
        Interval.open(sqrt(2), sqrt(2) + Rational(1, 10**7)),
        Interval(Rational(1, 3), Rational(1, 3) + Rational(1, 10**9)),
        Interval.open(sympy.CRootOf(x**5 - x - 1, 0), 2),
    ],
)
def test_rational_inside_is_strictly_inside(interval: Any) -> None:
    p = rational_inside(interval)
    assert isinstance(p, Rational)
    assert (interval.start < p) is sympy.true and (p < interval.end) is sympy.true
