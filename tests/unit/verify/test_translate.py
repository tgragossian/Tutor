from __future__ import annotations

from typing import Any

import pytest
import sympy
from support.mathjson import keys, mj
from sympy import Abs, E, Rational, cos, exp, log, pi, real_root, sec, sin

from mathtutor.verify.translate import (
    VARIABLE_ASSUMPTIONS,
    Constraint,
    Rejected,
    TranslateContext,
    Translated,
    translate,
)

CTX = TranslateContext()
X = sympy.Symbol("x", real=True)

# Every captured fixture key appears exactly once: expected expr or Rejected code.
CASES: dict[str, Any] = {
    "x_plain": X,
    "six_x_cos": 6 * X * cos(3 * X**2),
    "sin_of_2x": sin(2 * X),
    "typed_sin": sin(2 * X),
    "sin2x": sin(X) ** 2,
    "x2_sinx": X**2 * sin(X),
    "sec2": sec(X) ** 2,
    "tan_x": sympy.tan(X),
    "cot_x": sympy.cot(X),
    "frac_power": X ** Rational(3, 2),
    "neg_power": X**-2,
    "cuberoot": real_root(X, 3),
    "sqrt_x": sympy.sqrt(X),
    "typed_sqrt": sympy.sqrt(X),
    "sqrt_x2": sympy.sqrt(X**2),
    "ln_x": log(X),
    "ln_x2": log(X**2),
    "log_x": log(X, 10),
    "log10_x": log(X, 10),
    "lg_x": log(X, 10),
    "log2_x": log(X, 2),
    "loge_x": log(X),
    "exp_x2": exp(X**2),
    "exp_fn": exp(X),
    "pi_e": pi + E,
    "frac_pi_4": pi / 4,
    "abs_x": Abs(X),
    "paren_sq": (X + 1) ** 2,
    "implicit_mult": 2 * pi * X,
    "neg_half": Rational(-1, 2),
    "dec_inside": Rational(1, 2) / X,
    "dec_0780": Rational(78, 100),
    "typed_dec_0780": Rational(78, 100),
    "dec_0785": Rational(785, 1000),
    "dec_079": Rational(79, 100),
    "dec_250": Rational(5, 2),
    "num_3": sympy.Integer(3),
    "rational_fn": (X**2 - 1) / (X - 1),
    "typed_frac": 1 / X,
    "typed_pow": X**2 + 1,
    # Bare "x": the placeholder was lost in capture; precheck catches it from the LaTeX.
    "incomplete": X,
    "typed_pow_empty": X,
    "matrix": "unsupported_notation",
    "set_pts": "unsupported_notation",
    "f_of_2x": "unsupported_notation",
    "product_rule": "unsupported_notation",
    "arcsin": "unsupported_notation",
    "sin_inv": "unsupported_notation",
    "inf": "unsupported_notation",
    "dne": "unsupported_notation",
    "empty": "unsupported_notation",
    "typed_frac_empty": "unsupported_notation",
    "antideriv_c": "unsupported_notation",
    "huge_pow": "input_too_large",
    "long_int": "input_too_large",
}


def ok(tree: Any) -> Translated:
    result = translate(tree, CTX)
    assert isinstance(result, Translated), result
    return result


def code(tree: Any) -> str:
    result = translate(tree, CTX)
    assert isinstance(result, Rejected), result
    return str(result.code)


def same(a: sympy.Expr, b: sympy.Expr) -> bool:
    return bool(sympy.simplify(a - b) == 0)


def has(t: Translated, kind: str, expr: sympy.Expr) -> bool:
    return any(c.kind == kind and same(c.expr, expr) for c in t.constraints)


def test_cases_cover_every_captured_key() -> None:
    assert set(CASES) == set(keys())


@pytest.mark.parametrize("key", sorted(CASES))
def test_captured_fixture_translates(key: str) -> None:
    expected = CASES[key]
    if isinstance(expected, str):
        assert code(mj(key)) == expected
    else:
        assert same(ok(mj(key)).expr, expected)


def test_variable_is_real_symbol() -> None:
    assert VARIABLE_ASSUMPTIONS == {"real": True}
    assert ok("x").expr == X
    t = translate("t", TranslateContext(variable="t"))
    assert isinstance(t, Translated) and t.expr == sympy.Symbol("t", real=True)


def test_constraints_come_from_raw_tree() -> None:
    t = ok(mj("rational_fn"))
    assert has(t, "nonzero", X - 1)


def test_constraint_kinds() -> None:
    assert has(ok(mj("ln_x")), "positive", X)
    assert has(ok(mj("log_x")), "positive", X)
    assert has(ok(mj("log2_x")), "positive", X)
    assert has(ok(mj("sqrt_x")), "nonnegative", X)
    assert has(ok(["Root", "x", 4]), "nonnegative", X)
    assert has(ok(mj("tan_x")), "not_half_pi_odd", X)
    assert has(ok(mj("sec2")), "not_half_pi_odd", X)
    assert has(ok(mj("cot_x")), "not_pi_multiple", X)
    assert has(ok(["Csc", ["Multiply", 2, "x"]]), "not_pi_multiple", 2 * X)
    assert has(ok(mj("neg_power")), "nonzero", X)
    assert has(ok(mj("frac_power")), "nonnegative", X)
    assert has(ok(["Power", "x", ["Negate", ["Divide", 1, 2]]]), "positive", X)


def test_no_constraint_where_defined_everywhere() -> None:
    for tree in (mj("cuberoot"), mj("abs_x"), mj("exp_fn"), mj("exp_x2"), ["Cos", "x"]):
        assert ok(tree).constraints == ()
    assert ok(["Power", 2, "x"]).constraints == ()
    assert ok(["Divide", "Pi", 4]).constraints == ()


def test_nested_constraints_all_collected() -> None:
    t = ok(["Ln", ["Divide", 1, ["Sqrt", ["Tan", "x"]]]])
    assert has(t, "positive", 1 / sympy.sqrt(sympy.tan(X)))
    assert has(t, "nonzero", sympy.sqrt(sympy.tan(X)))
    assert has(t, "nonnegative", sympy.tan(X))
    assert has(t, "not_half_pi_odd", X)


def test_nonconstant_exponent_needs_positive_base() -> None:
    assert has(ok(["Power", "x", "x"]), "positive", X)
    assert has(ok(["Power", "x", "Pi"]), "positive", X)


def test_nonconstant_log_base() -> None:
    t = ok(["Log", 8, "x"])
    assert has(t, "positive", X)
    assert has(t, "nonzero", X - 1)
    assert same(t.expr, log(8) / log(X))


def test_constant_violation_is_kept_as_constraint() -> None:
    assert has(ok(["Divide", 1, 0]), "nonzero", sympy.Integer(0))
    assert has(ok(["Ln", ["Negate", 1]]), "positive", sympy.Integer(-1))


def test_power_exponent_bound_both_sides() -> None:
    assert isinstance(translate(["Power", "x", 200], CTX), Translated)
    assert code(["Power", "x", 201]) == "input_too_large"
    assert code(["Power", "x", 1000]) == "input_too_large"
    assert code(["Power", ["Power", "x", 20], 11]) == "input_too_large"
    assert isinstance(translate(["Power", ["Power", "x", 20], 10], CTX), Translated)
    assert code(["Power", ["Sqrt", ["Power", "x", 20]], 11]) == "input_too_large"
    assert isinstance(translate(["Power", 2, 1000], CTX), Translated)
    assert code(["Power", 2, 1001]) == "input_too_large"
    assert code(["Power", "Pi", ["Negate", 1001]]) == "input_too_large"


def test_const_digits_bound() -> None:
    assert isinstance(translate(["Power", 10, 999], CTX), Translated)
    assert code(["Power", 10, 1000]) == "input_too_large"
    assert code(["Power", ["Divide", 1, 10], 1000]) == "input_too_large"
    assert code(["Power", ["Power", 10, 500], 3]) == "input_too_large"
    assert code(["Power", 10, ["Power", 10, 10]]) == "input_too_large"


def test_inexact_constant_exponent_bounded_by_magnitude() -> None:
    assert isinstance(translate(["Power", "x", "Pi"], CTX), Translated)
    # sqrt(4)^1000 evaluates to an integer; it must not slip through as an exponent.
    assert code(["Power", 2, ["Power", ["Sqrt", 4], 1000]]) == "input_too_large"
    assert code(["Power", 2, ["Exp", ["Ln", ["Power", 10, 30]]]]) == "input_too_large"


def test_nonconstant_exponent_allowed() -> None:
    assert isinstance(translate(["Power", 2, "x"], CTX), Translated)
    assert code(["Power", 2, ["Power", "x", 201]]) == "input_too_large"


def test_other_symbol_rejected() -> None:
    result = translate(["Add", "x", "y"], CTX)
    assert isinstance(result, Rejected) and result.code == "unsupported_notation"


@pytest.mark.parametrize(
    "tree",
    [
        ["Sin"],
        ["Sin", "x", "x"],
        ["Divide", 1],
        ["Power", "x"],
        ["Subtract", "x"],
        ["Add", "x"],
        ["Log", "x", 2, 3],
        ["Delimiter"],
        ["Delimiter", "x", "'[]'"],
        ["Root", "x", 0],
        ["Root", "x", ["Divide", 1, 2]],
        ["Root", "x", "x"],
        ["Rational", 1, 0],
        ["Rational", "x", 2],
        ["InvisibleOperator", "e", ["Delimiter", "x"]],
        ["InvisibleOperator", 2, ["Divide", 1, 2]],
        ["InvisibleOperator", "x", 2],
        ["Multiply", "x", 1.5],
        "Infinity",
        "ExponentialE2",
        {"num": "abc"},
        {"rational": [1, 2]},
        [["Sin"], "x"],
        True,
        None,
    ],
)
def test_bad_shapes_rejected(tree: Any) -> None:
    assert code(tree) == "unsupported_notation"


def test_accepted_heads() -> None:
    assert same(ok(["Rational", 3, 4]).expr, Rational(3, 4))
    assert same(ok(["Multiply", 2, "x"]).expr, 2 * X)
    assert same(ok(["Subtract", "x", 1]).expr, X - 1)
    assert same(ok(["Negate", "x"]).expr, -X)
    assert same(ok("ExponentialE").expr, E)
    assert same(ok(["Exp", 1]).expr, E)
    assert same(ok(["Root", "x", 4]).expr, X ** Rational(1, 4))
    assert same(ok(["Root", ["Negate", 8], 3]).expr, sympy.Integer(-2))
    assert same(ok(["Log", "x", "Pi"]).expr, log(X) / log(pi))
    assert same(ok(["InvisibleOperator", "x", ["Delimiter", ["Add", "x", 1]]]).expr, X * (X + 1))
    assert same(ok({"num": "1.5e-3"}).expr, Rational(3, 2000))
    assert same(ok({"num": "-0.25"}).expr, Rational(-1, 4))


def test_decimal_is_exact() -> None:
    expr = ok({"num": "0.1"}).expr
    assert expr == Rational(1, 10)


def test_no_evaluation_during_build() -> None:
    expr = ok(["Power", 2, 1000]).expr
    assert isinstance(expr, sympy.Pow)
    assert expr.args == (sympy.Integer(2), sympy.Integer(1000))
    product = ok(["Multiply", 2, 3]).expr
    assert isinstance(product, sympy.Mul) and product.args == (2, 3)


def test_structural_issues_mapped() -> None:
    nested: Any = "x"
    for _ in range(31):
        nested = ["Negate", nested]
    assert code(nested) == "input_too_large"
    assert code(["Add", *["x"] * 200]) == "input_too_large"


def test_constraint_is_frozen_value() -> None:
    c = Constraint("nonzero", X)
    assert c == Constraint("nonzero", X)
    with pytest.raises(AttributeError):
        c.kind = "positive"  # type: ignore[misc]
