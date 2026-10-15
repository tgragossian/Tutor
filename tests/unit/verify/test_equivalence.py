from __future__ import annotations

import time
from typing import Any

import pytest
import sympy
from sympy import ConditionSet, FiniteSet, Interval, Rational, oo, pi

from mathtutor.content.schema import Domain
from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify import equivalence
from mathtutor.verify.equivalence import (
    Budget,
    Gap,
    equivalent,
    prove_equal,
    removable_at,
    to_sympy_set,
    violation_set,
)
from mathtutor.verify.translate import (
    VARIABLE_ASSUMPTIONS,
    Constraint,
    TranslateContext,
    Translated,
    translate,
)
from mathtutor.verify.types import Verdict

x = sympy.Symbol("x", **VARIABLE_ASSUMPTIONS)
CTX = TranslateContext()

REALS = Domain()
POSITIVE = Domain(intervals=[("0", "inf", "open", "open")])
NONZERO = Domain(intervals=[("-inf", "0", "open", "open"), ("0", "inf", "open", "open")])
ZERO_TO_TWO = Domain(intervals=[("0", "2", "open", "open")])
NEAR_ZERO = Domain(intervals=[("-3/2", "3/2", "open", "open")])
REALS_BUT_ONE = Domain(exclude=["1"])

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
DOMAIN_UNPROVEN = Verdict(
    VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.DOMAIN_UNPROVEN, Method.DOMAIN
)
UNDEFINED_ON_DOMAIN = Verdict(
    VerdictStatus.INCORRECT, VerdictReason.UNDEFINED_ON_DOMAIN, Method.DOMAIN
)

# MathJSON trees, as the browser sends them.
RATIONAL_FN = ["Divide", ["Subtract", ["Power", "x", 2], 1], ["Subtract", "x", 1]]
RATIONAL_FN_DOUBLED = [
    "Divide",
    ["Subtract", ["Multiply", 2, ["Power", "x", 2]], 2],
    ["Subtract", ["Multiply", 2, "x"], 2],
]
X_PLUS_1 = ["Add", "x", 1]
SIN2_PLUS_COS2 = ["Add", ["Power", ["Sin", "x"], 2], ["Power", ["Cos", "x"], 2]]
ONE = 1
LN_X2 = ["Ln", ["Power", "x", 2]]
TWO_LN_X = ["Multiply", 2, ["Ln", "x"]]
SQRT_X2 = ["Sqrt", ["Power", "x", 2]]
SQRT_X_SQUARED = ["Power", ["Sqrt", "x"], 2]
X = "x"
CUBE_ROOT = ["Power", "x", ["Rational", 1, 3]]
ROOT_3 = ["Root", "x", 3]
CUBE_ROOT_CUBED = ["Power", CUBE_ROOT, 3]
TWO_THIRDS = ["Power", "x", ["Rational", 2, 3]]
SQUARE_CUBE_ROOT = ["Power", ["Power", "x", 2], ["Rational", 1, 3]]
ABS_CUBE_ROOT = ["Power", ["Abs", "x"], ["Rational", 1, 3]]
TAN_COS = ["Multiply", ["Tan", "x"], ["Cos", "x"]]
SIN = ["Sin", "x"]
ONE_PLUS_TAN2 = ["Add", 1, ["Power", ["Tan", "x"], 2]]
SEC2 = ["Power", ["Sec", "x"], 2]
X_MINUS_COS = ["Subtract", "x", ["Cos", "x"]]
SELF_RATIO = ["Divide", X_MINUS_COS, X_MINUS_COS]


def tr(tree: Any) -> Translated:
    result = translate(tree, CTX)
    assert isinstance(result, Translated), result
    return result


def fresh() -> Budget:
    return Budget(time.monotonic() + 60)


def eq(student: Any, expected: Any, domain: Domain = REALS, strict: bool = False) -> Any:
    return equivalent(tr(student), tr(expected), domain, strict, x, fresh())


# -- spec 04 consequences --------------------------------------------------------------------


def test_removable_hole_default() -> None:
    """Spec 04: x + 1 vs (x²−1)/(x−1) on ℝ → correct (removable hole at 1)."""
    assert eq(RATIONAL_FN, X_PLUS_1) == Verdict("correct", "proven", "symbolic")


def test_removable_hole_strict() -> None:
    """Spec 04: x + 1 vs (x²−1)/(x−1) on ℝ, strict → incorrect (undefined_on_domain)."""
    assert eq(RATIONAL_FN, X_PLUS_1, strict=True) == UNDEFINED_ON_DOMAIN


def test_sin2_plus_cos2_is_one() -> None:
    """Spec 04: sin²x + cos²x vs 1 on ℝ → correct (simplify)."""
    assert eq(SIN2_PLUS_COS2, ONE) == CORRECT


def test_log_branch_on_positive_reals() -> None:
    """Spec 04: 2 ln x vs ln(x²) on (0, ∞) → correct."""
    assert eq(LN_X2, TWO_LN_X, domain=POSITIVE) == CORRECT


def test_log_branch_on_nonzero_reals_not_proven() -> None:
    """Spec 04: ln(x²) vs 2 ln x on ℝ \\ {0} → not proven here (task 5 refutes)."""
    assert eq(TWO_LN_X, LN_X2, domain=NONZERO) is None


def test_sqrt_x2_not_proven_equal_to_x() -> None:
    """Spec 04: x vs √(x²) on ℝ → not proven here (task 5 finds the counterexample)."""
    assert eq(SQRT_X2, X) is None


def test_sqrt_x_squared_is_gap_on_reals() -> None:
    """Spec 04 step 2: a violated subinterval where E is defined → Gap for task 5."""
    result = eq(SQRT_X_SQUARED, X)
    assert result == Gap(Interval.open(-oo, 0))


def test_sqrt_x_squared_on_positive_reals_is_correct() -> None:
    """Spec 04 step 2: the violation set misses D entirely → correct."""
    assert eq(SQRT_X_SQUARED, X, domain=POSITIVE) == CORRECT


def test_excluded_point_ignored() -> None:
    """Spec 04 step 2: holes outside D (an excluded point) never count, even when strict."""
    assert eq(RATIONAL_FN, X_PLUS_1, domain=REALS_BUT_ONE, strict=True) == CORRECT


def test_hole_shared_with_expected_is_ignored() -> None:
    """Spec 04 step 2: a hole where E is itself undefined is not the student's error."""
    assert eq(RATIONAL_FN, RATIONAL_FN_DOUBLED, strict=True) == CORRECT


def test_wrong_answers_are_not_proven() -> None:
    """Spec 04 step 1: no strategy returns 0 for a wrong formula."""
    assert eq(["Add", "x", 1], X) is None
    assert eq(SIN, ["Cos", "x"]) is None
    assert eq(["Add", "x", ["Divide", 1, 1000000000]], X) is None


# -- trig constraints (ImageSet violation sets) ----------------------------------------------


def test_imageset_on_reals_is_domain_unproven() -> None:
    """Spec 04 step 2: an infinite violation set (ImageSet) → domain_unproven."""
    assert eq(TAN_COS, SIN) == DOMAIN_UNPROVEN


def test_imageset_meets_bounded_domain_in_a_removable_point() -> None:
    """Spec 04 step 2: intersecting with D leaves {π/2}; the hole is removable."""
    assert eq(TAN_COS, SIN, domain=ZERO_TO_TWO) == CORRECT
    assert eq(TAN_COS, SIN, domain=ZERO_TO_TWO, strict=True) == UNDEFINED_ON_DOMAIN


def test_imageset_misses_bounded_domain() -> None:
    """Spec 04 step 2: no odd multiple of π/2 in (−3/2, 3/2) → correct even when strict."""
    assert eq(TAN_COS, SIN, domain=NEAR_ZERO, strict=True) == CORRECT


def test_constraint_shared_with_expected_is_ignored() -> None:
    """Spec 04 step 2: the student is undefined only where E is undefined → correct."""
    assert eq(ONE_PLUS_TAN2, SEC2) == CORRECT


def test_conditionset_is_domain_unproven() -> None:
    """Spec 04 step 2: x = cos x has no closed form, so solveset gives a ConditionSet."""
    assert eq(SELF_RATIO, ONE) == DOMAIN_UNPROVEN


# -- real roots (owner ruling R14) -----------------------------------------------------------


def test_cube_root_power_equals_root() -> None:
    """R14: x^(1/3) and Root(x, 3) are the same real root."""
    assert eq(CUBE_ROOT, ROOT_3) == CORRECT
    assert eq(ROOT_3, CUBE_ROOT) == CORRECT


def test_cube_root_cubed_never_wrongly_graded() -> None:
    """R14: (x^(1/3))³ = x on ℝ; either proven or not proven, never anything else."""
    assert eq(CUBE_ROOT_CUBED, X) in (CORRECT, None)


def test_two_thirds_power_never_wrongly_graded() -> None:
    """R14: x^(2/3) = (x²)^(1/3) on ℝ; either proven or not proven, never anything else."""
    assert eq(TWO_THIRDS, SQUARE_CUBE_ROOT) in (CORRECT, None)
    assert eq(SQUARE_CUBE_ROOT, TWO_THIRDS) in (CORRECT, None)


def test_real_root_differs_from_abs_root() -> None:
    """R14: x^(1/3) ≠ |x|^(1/3) for x < 0, so equality is never proven."""
    assert eq(CUBE_ROOT, ABS_CUBE_ROOT) is None
    assert eq(ABS_CUBE_ROOT, CUBE_ROOT) is None
    assert eq(CUBE_ROOT, ["Negate", CUBE_ROOT]) is None


# -- helpers ---------------------------------------------------------------------------------


def test_to_sympy_set() -> None:
    """Spec 01 domain: union of intervals minus the excluded points."""
    assert to_sympy_set(REALS) == sympy.S.Reals
    assert to_sympy_set(REALS_BUT_ONE) == Interval.open(-oo, 1) | Interval.open(1, oo)
    closed = Domain(intervals=[("-1/2", "3", "closed", "open")], exclude=["0"])
    assert to_sympy_set(closed) == Interval.Ropen(Rational(-1, 2), 0) | Interval.open(0, 3)


def test_violation_sets() -> None:
    """Spec 04 step 2: the set in D where each constraint kind fails."""
    reals = sympy.S.Reals
    assert violation_set(Constraint("nonzero", x - 1), x, reals) == FiniteSet(1)
    assert violation_set(Constraint("positive", x), x, reals) == Interval(-oo, 0)
    assert violation_set(Constraint("nonnegative", x), x, reals) == Interval.open(-oo, 0)
    assert violation_set(Constraint("not_half_pi_odd", x), x, Interval(0, 2)) == FiniteSet(pi / 2)
    assert violation_set(Constraint("not_pi_multiple", x), x, Interval.open(0, 4)) == FiniteSet(pi)
    assert isinstance(
        violation_set(Constraint("nonzero", x - sympy.cos(x)), x, reals), ConditionSet
    )


def test_removable_at() -> None:
    """Spec 04 step 2: both one-sided limits exist, are finite and equal E(h)."""
    assert removable_at((x**2 - 1) / (x - 1), x + 1, x, Rational(1))


def test_pole_not_removable() -> None:
    """Spec 04 step 2: an infinite limit is not a removable hole."""
    assert not removable_at(x + 1 / (x - 1), x, x, Rational(1))


def test_jump_not_removable() -> None:
    """Spec 04 step 2: one-sided limits that differ are not a removable hole."""
    assert not removable_at(sympy.Abs(x) / x, sympy.Integer(1), x, Rational(0))


def test_spent_budget_returns_none() -> None:
    """Spec 04 step 1: a spent budget stops before any strategy runs."""
    assert prove_equal(x, x, Budget(time.monotonic() - 1)) is False


def test_spent_budget_in_equivalent_returns_none() -> None:
    """Spec 04 step 1: an unproven equality is None, never a verdict."""
    spent = Budget(time.monotonic() - 1)
    assert equivalent(tr(X), tr(X), REALS, False, x, spent) is None


def test_spent_budget_in_domain_step_is_domain_unproven(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spec 04 step 2: the domain step abstains when the budget runs out."""

    def proven_then_spent(s: Any, e: Any, budget: Budget) -> bool:
        budget.deadline = time.monotonic() - 1
        return True

    monkeypatch.setattr(equivalence, "prove_equal", proven_then_spent)
    result = equivalent(tr(RATIONAL_FN), tr(X_PLUS_1), REALS, False, x, fresh())
    assert result == DOMAIN_UNPROVEN


def test_budget_remaining() -> None:
    assert Budget(time.monotonic() + 100).remaining() > 99
    assert Budget(time.monotonic() - 1).remaining() < 0


# -- untrusted solveset (review C1, ruling R18) ----------------------------------------------

TWO_THIRDS_OF_X = ["Power", "x", ["Rational", 2, 3]]
ONE_MINUS_TT = ["Subtract", 1, TWO_THIRDS_OF_X]
TT_MINUS_ONE = ["Subtract", TWO_THIRDS_OF_X, 1]


@pytest.mark.parametrize(
    "student,expected,strict",
    [
        (["Power", ["Sqrt", ONE_MINUS_TT], 2], ONE_MINUS_TT, False),
        (["Add", "x", ["Subtract", ["Ln", ONE_MINUS_TT], ["Ln", ONE_MINUS_TT]]], X, False),
        (["Divide", ["Multiply", "x", TT_MINUS_ONE], TT_MINUS_ONE], X, True),
    ],
)
def test_real_root_constraints_never_falsely_correct(
    student: Any, expected: Any, strict: bool
) -> None:
    """R18 (a): solveset mis-solves |a|^(p/q); such constraints abstain, never correct."""
    result = eq(student, expected, strict=strict)
    assert result != CORRECT
    assert result == DOMAIN_UNPROVEN or isinstance(result, Gap) or result == UNDEFINED_ON_DOMAIN


def test_wrong_empty_solveset_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """R18 (b): a sampled violation outside solveset's answer → domain_unproven."""
    monkeypatch.setattr(equivalence.sympy, "solveset", lambda *args, **kwargs: sympy.S.EmptySet)
    assert eq(SQRT_X_SQUARED, X) == DOMAIN_UNPROVEN
    assert eq(RATIONAL_FN, X_PLUS_1) == DOMAIN_UNPROVEN


def test_spurious_solveset_point_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """R18 (b): a sampled point solveset calls violated where the constraint holds."""
    monkeypatch.setattr(equivalence.sympy, "solveset", lambda *args, **kwargs: FiniteSet(1, 2))
    assert eq(RATIONAL_FN, X_PLUS_1, strict=True) == DOMAIN_UNPROVEN
