from __future__ import annotations

import sympy

from mathtutor.verify.rewrite import reduce_constraint
from mathtutor.verify.translate import Constraint

X = sympy.Symbol("x", real=True)


def test_cos_nonzero_becomes_half_pi_lattice() -> None:
    got = reduce_constraint(Constraint("nonzero", sympy.cos(3 * X + 1)))
    assert got == (Constraint("not_half_pi_odd", 3 * X + 1),)


def test_sin_and_tan_nonzero_become_pi_lattice() -> None:
    for fn in (sympy.sin, sympy.tan):
        got = reduce_constraint(Constraint("nonzero", fn(X / 3)))
        assert got == (Constraint("not_pi_multiple", X / 3),)


def test_product_and_power_split() -> None:
    product = sympy.Mul(3, sympy.sin(X / 3), evaluate=False)
    got = reduce_constraint(Constraint("nonzero", product))
    assert set(got) == {
        Constraint("nonzero", sympy.Integer(3)),
        Constraint("not_pi_multiple", X / 3),
    }
    got = reduce_constraint(Constraint("nonzero", sympy.cos(X) ** 2))
    assert got == (Constraint("not_half_pi_odd", X),)


def test_exp_always_holds() -> None:
    for kind in ("positive", "nonnegative", "nonzero"):
        assert reduce_constraint(Constraint(kind, sympy.exp(X))) == ()  # type: ignore[arg-type]


def test_abs_reduces_to_inner_nonzero() -> None:
    for kind in ("positive", "nonzero"):
        got = reduce_constraint(Constraint(kind, sympy.Abs(X)))  # type: ignore[arg-type]
        assert got == (Constraint("nonzero", X),)
    assert reduce_constraint(Constraint("nonnegative", sympy.Abs(X))) == ()


def test_unmatched_is_unchanged() -> None:
    unmatched = [
        Constraint("positive", sympy.cos(X)),
        Constraint("nonnegative", X - 1),
        Constraint("nonzero", sympy.Pow(X, sympy.Rational(1, 2), evaluate=False)),
        Constraint("positive", sympy.Pow(sympy.Abs(X), sympy.Rational(1, 2), evaluate=False)),
    ]
    for c in unmatched:
        assert reduce_constraint(c) == (c,)


def test_trig_kinds_are_never_rewritten() -> None:
    for kind in ("not_pi_multiple", "not_half_pi_odd"):
        for inner in (sympy.exp(X), sympy.Abs(X)):
            c = Constraint(kind, inner)  # type: ignore[arg-type]
            assert reduce_constraint(c) == (c,)


def test_e_power_written_as_pow_always_holds() -> None:
    power = sympy.Pow(sympy.E, X, evaluate=False)
    for kind in ("positive", "nonnegative", "nonzero"):
        assert reduce_constraint(Constraint(kind, power)) == ()  # type: ignore[arg-type]
    c = Constraint("not_pi_multiple", power)
    assert reduce_constraint(c) == (c,)
