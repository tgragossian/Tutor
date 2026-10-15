"""Allowlist translation of raw MathJSON into SymPy (spec 03). Runs only in verifier workers.

This is the only place untrusted math becomes SymPy objects. Every node is built with
``evaluate=False`` after a bottom-up cost estimate, and the domain constraints are read
from the raw tree before anything could cancel them.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Any, Literal

import sympy
from pydantic import JsonValue

from mathtutor.domain import FormatIssueCode
from mathtutor.verify.structure import check_structure

ConstraintKind = Literal["nonzero", "positive", "nonnegative", "not_half_pi_odd", "not_pi_multiple"]

VARIABLE_ASSUMPTIONS = {"real": True}

MAX_EXPONENT = 1000
MAX_CONST_DIGITS = 1000
MAX_DEGREE = 200
MAX_ROOT_INDEX = 1000
# Digit estimates saturate here; anything this large is already far past every bound.
_DIGITS_CAP = 10**6
_LOG10_2 = 0.30103  # slightly above log10(2), so digit estimates stay upper bounds


@dataclass(frozen=True)
class Constraint:
    """``expr`` must satisfy ``kind`` wherever the translated expression is defined."""

    kind: ConstraintKind
    expr: sympy.Expr


@dataclass(frozen=True)
class Translated:
    expr: sympy.Expr
    constraints: tuple[Constraint, ...]


@dataclass(frozen=True)
class Rejected:
    code: FormatIssueCode
    detail: str


@dataclass(frozen=True)
class TranslateContext:
    variable: str = "x"


class _Reject(Exception):
    def __init__(self, code: FormatIssueCode, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


def _unsupported(detail: str) -> _Reject:
    return _Reject(FormatIssueCode.UNSUPPORTED_NOTATION, detail)


def _too_large(detail: str) -> _Reject:
    return _Reject(FormatIssueCode.INPUT_TOO_LARGE, detail)


@dataclass(frozen=True)
class _Node:
    """A translated subtree with its cost estimate.

    ``value``: the exact value when the subtree is rational arithmetic on literals.
    ``digits``: for a constant subtree, an upper bound on the decimal digits of any number
    SymPy may materialise from it (numerator and denominator alike); None if not constant.
    ``degree``: an upper bound on the polynomial degree in the variable (0 for constants).
    """

    expr: Any
    value: Fraction | None
    digits: int | None
    degree: int

    @property
    def constant(self) -> bool:
        return self.digits is not None


def _int_digits(n: int) -> int:
    return max(1, int(abs(n).bit_length() * _LOG10_2) + 1)


def _frac_digits(v: Fraction) -> int:
    return max(_int_digits(v.numerator), _int_digits(v.denominator))


def _cap(n: int) -> int:
    return min(n, _DIGITS_CAP)


def _const(expr: Any, value: Fraction | None, digits: int) -> _Node:
    if value is not None:
        digits = _frac_digits(value)
    return _Node(expr, value, _cap(digits), 0)


def _rational(v: Fraction) -> Any:
    return sympy.Rational(v.numerator, v.denominator)


def _is_named_constant(node: _Node) -> bool:
    return node.expr is sympy.pi or node.expr is sympy.E


def _satisfied(kind: ConstraintKind, node: _Node) -> bool:
    """True only when the constraint is known to hold (pi and e are positive and not 1)."""
    v = node.value
    if _is_named_constant(node):
        return kind != "not_half_pi_odd" and kind != "not_pi_multiple"
    if v is None:
        return False
    if kind == "nonzero" or kind == "not_pi_multiple":
        return v != 0
    if kind == "positive":
        return v > 0
    if kind == "nonnegative":
        return v >= 0
    return True  # a rational is never pi/2 + k*pi


def _is_literal(tree: JsonValue) -> bool:
    return (isinstance(tree, int) and not isinstance(tree, bool)) or isinstance(tree, dict)


def _is_literal_fraction(tree: JsonValue) -> bool:
    return (
        isinstance(tree, list)
        and len(tree) == 3
        and tree[0] in ("Divide", "Rational")
        and _is_literal(tree[1])
        and _is_literal(tree[2])
    )


class _Builder:
    def __init__(self, ctx: TranslateContext) -> None:
        self.variable = ctx.variable
        self.symbol = sympy.Symbol(ctx.variable, **VARIABLE_ASSUMPTIONS)
        self.constraints: list[Constraint] = []
        self.heads: dict[str, tuple[int, int, Callable[[list[JsonValue]], _Node]]] = {
            "Add": (2, 200, self._add),
            "Subtract": (2, 2, self._subtract),
            "Negate": (1, 1, self._negate),
            "Multiply": (2, 200, self._multiply),
            "InvisibleOperator": (2, 200, self._invisible),
            "Divide": (2, 2, self._divide),
            "Rational": (2, 2, self._rational_head),
            "Power": (2, 2, self._power),
            "Sqrt": (1, 1, self._sqrt),
            "Root": (2, 2, self._root),
            "Sin": (1, 1, self._trig(sympy.sin, None)),
            "Cos": (1, 1, self._trig(sympy.cos, None)),
            "Tan": (1, 1, self._trig(sympy.tan, "not_half_pi_odd")),
            "Sec": (1, 1, self._trig(sympy.sec, "not_half_pi_odd")),
            "Cot": (1, 1, self._trig(sympy.cot, "not_pi_multiple")),
            "Csc": (1, 1, self._trig(sympy.csc, "not_pi_multiple")),
            "Ln": (1, 1, self._ln),
            "Log": (1, 2, self._log),
            "Lb": (1, 1, self._lb),
            "Exp": (1, 1, self._exp),
            "Abs": (1, 1, self._abs),
            "Delimiter": (1, 1, lambda args: self.walk(args[0])),
        }

    # -- constraints -------------------------------------------------------------------------

    def require(self, kind: ConstraintKind, node: _Node) -> None:
        if _satisfied(kind, node):
            return
        constraint = Constraint(kind, node.expr)
        if constraint not in self.constraints:
            self.constraints.append(constraint)

    # -- dispatch ----------------------------------------------------------------------------

    def walk(self, tree: JsonValue) -> _Node:
        if isinstance(tree, bool) or tree is None or isinstance(tree, float):
            raise _unsupported("unsupported value")
        if isinstance(tree, int):
            return _const(sympy.Integer(tree), Fraction(tree), 0)
        if isinstance(tree, dict):
            literal = tree.get("num")
            if len(tree) != 1 or not isinstance(literal, str):
                raise _unsupported("unsupported object")
            value = Fraction(Decimal(literal))
            return _const(_rational(value), value, 0)
        if isinstance(tree, str):
            return self._symbol(tree)
        if not tree or not isinstance(tree[0], str):
            raise _unsupported("operator must be a name")
        head, args = tree[0], tree[1:]
        entry = self.heads.get(head)
        if entry is None:
            raise _unsupported(f"unsupported operator {head[:40]!r}")
        low, high, handler = entry
        if not low <= len(args) <= high:
            raise _unsupported(f"{head} takes {low}..{high} arguments")
        return handler(args)

    def _symbol(self, name: str) -> _Node:
        if name == self.variable:
            return _Node(self.symbol, None, None, 1)
        if name == "Pi":
            return _const(sympy.pi, None, 1)
        if name in ("e", "ExponentialE"):
            return _const(sympy.E, None, 1)
        raise _unsupported(f"unknown symbol {name[:40]!r}")

    # -- arithmetic --------------------------------------------------------------------------

    def _sum(self, nodes: list[_Node]) -> _Node:
        expr = sympy.Add(*(n.expr for n in nodes), evaluate=False)
        if all(n.constant for n in nodes):
            value: Fraction | None = Fraction(0)
            for n in nodes:
                value = value + n.value if value is not None and n.value is not None else None
            return _const(expr, value, sum(n.digits or 0 for n in nodes) + 1)
        return _Node(expr, None, None, max(n.degree for n in nodes))

    def _product(self, expr: Any, nodes: list[_Node], value: Fraction | None) -> _Node:
        if all(n.constant for n in nodes):
            return _const(expr, value, sum(n.digits or 0 for n in nodes))
        return _Node(expr, None, None, sum(n.degree for n in nodes))

    def _add(self, args: list[JsonValue]) -> _Node:
        return self._sum([self.walk(a) for a in args])

    def _negated(self, node: _Node) -> _Node:
        expr = sympy.Mul(sympy.Integer(-1), node.expr, evaluate=False)
        value = -node.value if node.value is not None else None
        return _Node(expr, value, node.digits, node.degree)

    def _subtract(self, args: list[JsonValue]) -> _Node:
        return self._sum([self.walk(args[0]), self._negated(self.walk(args[1]))])

    def _negate(self, args: list[JsonValue]) -> _Node:
        return self._negated(self.walk(args[0]))

    def _multiply(self, args: list[JsonValue]) -> _Node:
        nodes = [self.walk(a) for a in args]
        value: Fraction | None = Fraction(1)
        for n in nodes:
            value = value * n.value if value is not None and n.value is not None else None
        return self._product(sympy.Mul(*(n.expr for n in nodes), evaluate=False), nodes, value)

    def _invisible(self, args: list[JsonValue]) -> _Node:
        for prev, cur in zip(args, args[1:], strict=False):
            letter = isinstance(prev, str) and len(prev) == 1 and prev.isalpha()
            delimited = isinstance(cur, list) and cur[:1] == ["Delimiter"]
            if letter and prev != self.variable and delimited:
                raise _unsupported("function application")
            if _is_literal(cur):
                raise _unsupported("number after a factor in an implicit product")
            if _is_literal(prev) and _is_literal_fraction(cur):
                raise _unsupported("mixed number")
        return self._multiply(args)

    def _divide(self, args: list[JsonValue]) -> _Node:
        num, den = self.walk(args[0]), self.walk(args[1])
        self.require("nonzero", den)
        inverse = sympy.Pow(den.expr, sympy.Integer(-1), evaluate=False)
        expr = sympy.Mul(num.expr, inverse, evaluate=False)
        value = None
        if num.value is not None and den.value is not None and den.value != 0:
            value = num.value / den.value
        return self._product(expr, [num, den], value)

    def _rational_head(self, args: list[JsonValue]) -> _Node:
        p, q = args
        if not (_is_int(p) and _is_int(q)) or q == 0:
            raise _unsupported("Rational takes two integers, the second nonzero")
        assert isinstance(p, int) and isinstance(q, int)
        value = Fraction(p, q)
        return _const(_rational(value), value, 0)

    # -- powers and roots --------------------------------------------------------------------

    def _power(self, args: list[JsonValue]) -> _Node:
        base, exp = self.walk(args[0]), self.walk(args[1])
        if not exp.constant:
            # Never expanded; real-valued only for a positive base.
            self.require("positive", base)
            expr = sympy.Pow(base.expr, exp.expr, evaluate=False)
            return _Node(expr, None, None, 1)
        v = exp.value
        if v is not None:
            if abs(v) > MAX_EXPONENT:
                raise _too_large(f"exponent exceeds {MAX_EXPONENT}")
            bound = math.ceil(abs(v))
        else:
            # Not rational arithmetic (pi, sqrt, exp, ...): |b| < 10^digits is all we know.
            assert exp.digits is not None
            if exp.digits > 3:
                raise _too_large(f"exponent may exceed {MAX_EXPONENT}")
            bound = 10**exp.digits
        if base.degree * bound > MAX_DEGREE:
            raise _too_large(f"polynomial degree may exceed {MAX_DEGREE}")
        digits = None
        if base.constant:
            digits = self._power_digits(base, bound)
            if digits > MAX_CONST_DIGITS:
                raise _too_large(f"constant may exceed {MAX_CONST_DIGITS} digits")
        if v is None:
            self.require("positive", base)
        elif v.denominator == 1 and v < 0:
            self.require("nonzero", base)
        elif v.denominator != 1:
            self.require("positive" if v < 0 else "nonnegative", base)
        exponent = _rational(v) if v is not None else exp.expr
        expr = sympy.Pow(base.expr, exponent, evaluate=False)
        if digits is None:
            return _Node(expr, None, None, base.degree * bound)
        value = None
        if base.value is not None and v is not None and v.denominator == 1:
            if base.value != 0 or v >= 0:
                value = base.value ** int(v)
        return _const(expr, value, digits)

    @staticmethod
    def _power_digits(base: _Node, bound: int) -> int:
        if base.value is None:
            assert base.digits is not None
            return base.digits * bound
        largest = max(abs(base.value.numerator), base.value.denominator)
        if largest <= 1 or bound == 0:
            return 1
        return math.floor(bound * math.log10(largest)) + 1

    def _sqrt(self, args: list[JsonValue]) -> _Node:
        node = self.walk(args[0])
        self.require("nonnegative", node)
        return self._like(node, sympy.Pow(node.expr, sympy.Rational(1, 2), evaluate=False))

    def _root(self, args: list[JsonValue]) -> _Node:
        node, index = self.walk(args[0]), self.walk(args[1])
        n = index.value
        if n is None or n.denominator != 1 or n < 2:
            raise _unsupported("root index must be an integer of at least 2")
        if n > MAX_ROOT_INDEX:
            raise _too_large(f"root index exceeds {MAX_ROOT_INDEX}")
        exponent = sympy.Rational(1, int(n))
        if n % 2 == 0:
            self.require("nonnegative", node)
            return self._like(node, sympy.Pow(node.expr, exponent, evaluate=False))
        # Odd root: the real root, sign(a) * |a|^(1/n) (what sympy.real_root gives for real a).
        magnitude = sympy.Pow(sympy.Abs(node.expr, evaluate=False), exponent, evaluate=False)
        expr = sympy.Mul(sympy.sign(node.expr, evaluate=False), magnitude, evaluate=False)
        return self._like(node, expr)

    @staticmethod
    def _like(node: _Node, expr: Any) -> _Node:
        """Same cost estimate as ``node`` (roots and Abs do not grow digits or degree)."""
        return _Node(expr, None, node.digits, node.degree)

    # -- functions ---------------------------------------------------------------------------

    @staticmethod
    def _apply(fn: Any, node: _Node, digits: int) -> _Node:
        expr = fn(node.expr, evaluate=False)
        if node.constant:
            return _const(expr, None, digits)
        return _Node(expr, None, None, 1)

    def _trig(self, fn: Any, kind: ConstraintKind | None) -> Callable[[list[JsonValue]], _Node]:
        def handler(args: list[JsonValue]) -> _Node:
            node = self.walk(args[0])
            if kind is not None:
                self.require(kind, node)
            return self._apply(fn, node, (node.digits or 0) + 1)

        return handler

    def _ln(self, args: list[JsonValue]) -> _Node:
        node = self.walk(args[0])
        self.require("positive", node)
        return self._apply(sympy.log, node, (node.digits or 0) + 1)

    def _log_base(self, arg: _Node, base: _Node) -> _Node:
        self.require("positive", arg)
        self.require("positive", base)
        if not (_is_named_constant(base) or (base.value is not None and base.value != 1)):
            one_off = sympy.Add(base.expr, sympy.Integer(-1), evaluate=False)
            self.require("nonzero", _Node(one_off, None, None, 0))
        if base.expr is sympy.E:
            return self._apply(sympy.log, arg, (arg.digits or 0) + 1)
        expr = sympy.Mul(
            sympy.log(arg.expr, evaluate=False),
            sympy.Pow(sympy.log(base.expr, evaluate=False), sympy.Integer(-1), evaluate=False),
            evaluate=False,
        )
        if arg.constant and base.constant:
            return _const(expr, None, (arg.digits or 0) + (base.digits or 0) + 1)
        return _Node(expr, None, None, 1)

    def _log(self, args: list[JsonValue]) -> _Node:
        arg = self.walk(args[0])
        base = self.walk(args[1]) if len(args) == 2 else self.walk(10)
        return self._log_base(arg, base)

    def _lb(self, args: list[JsonValue]) -> _Node:
        return self._log_base(self.walk(args[0]), self.walk(2))

    def _exp(self, args: list[JsonValue]) -> _Node:
        node = self.walk(args[0])
        digits = _DIGITS_CAP
        if node.value is not None and abs(node.value) <= _DIGITS_CAP:
            # e^|v| has at most |v| * log10(e) + 1 digits; 0.4343 > log10(e).
            digits = math.floor(abs(node.value) * Fraction(4343, 10000)) + 1
        elif node.digits is not None and node.digits <= 6:
            digits = 10**node.digits  # |a| < 10^d, so e^|a| has fewer than 10^d digits
        return self._apply(sympy.exp, node, digits)

    def _abs(self, args: list[JsonValue]) -> _Node:
        node = self.walk(args[0])
        expr = sympy.Abs(node.expr, evaluate=False)
        if node.value is not None:
            return _const(expr, abs(node.value), 0)
        return self._like(node, expr)


def _is_int(tree: JsonValue) -> bool:
    return isinstance(tree, int) and not isinstance(tree, bool)


def translate(tree: JsonValue, ctx: TranslateContext) -> Translated | Rejected:
    """Translate raw MathJSON through the allowlist. Never raises."""
    try:
        issue = check_structure(tree)
        if issue is not None:
            return Rejected(issue.code, issue.detail)
        builder = _Builder(ctx)
        node = builder.walk(tree)
        return Translated(node.expr, tuple(builder.constraints))
    except _Reject as rejection:
        return Rejected(rejection.code, rejection.detail)
    except Exception as error:  # any surprise in untrusted input is unsupported, never a crash
        return Rejected(FormatIssueCode.UNSUPPORTED_NOTATION, type(error).__name__)
