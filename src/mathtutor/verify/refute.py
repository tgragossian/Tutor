"""Certified refutation with interval arithmetic (spec 04 step 3). Runs only in verifier workers.

Expressions are enclosed by walking the translated SymPy tree with ``mpmath.iv`` at 60 digits.
``lambdify(..., modules=[iv])`` is not used: it prints ``Rational(1, 3)`` as the Python float
``1/3`` and ``sign`` as ``math.copysign``, so its "enclosures" are not rigorous. Any node the
walker cannot enclose soundly (an operation undefined somewhere in the box, an unknown head,
a value beyond the magnitude guard) makes the point skip; it never becomes a verdict.

A witness is certified only in two ways:
- ``counterexample``: at a point of D both enclosures are finite and disjoint;
- ``student_undefined``: on a whole neighbourhood of a point of D, a student ``positive`` or
  ``nonnegative`` constraint is violated (its enclosure lies on the violating side) while E's
  enclosure is finite. A point of D lies in a nondegenerate interval of D, so the
  neighbourhood meets D in positive measure: the student is missing part of the domain.
  Isolated violations (``nonzero``, the trig kinds) are never witnesses, since outside strict
  mode such a hole may be removable and the answer correct (spec 04 step 2).
"""

from __future__ import annotations

import random
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from fractions import Fraction
from typing import Any

import mpmath
import sympy
from mpmath import iv

from mathtutor.content.schema import Domain
from mathtutor.domain import VerdictReason
from mathtutor.verify.equivalence import Budget
from mathtutor.verify.translate import Translated

DPS = 60
_LIMIT = mpmath.mpf(2) ** 4000  # magnitude guard: larger values skip the point
_EXP_LIMIT = 10_000  # exp(10^4) is already beyond the guard
_HALF_WIDTH = sympy.Rational(1, 2**40)  # half-width of the student_undefined neighbourhood

Box = tuple[Any, Any]  # exact mpf endpoints (lo, hi) of an enclosure


class _Skip(Exception):
    """The node cannot be enclosed soundly here."""


# -- the interval evaluator ------------------------------------------------------------------


@contextmanager
def _working_precision(dps: int = DPS) -> Iterator[None]:
    saved = iv.dps
    iv.dps = dps
    try:
        yield
    finally:
        iv.dps = saved


def _ends(v: Any) -> Box:
    lo, hi = v._mpi_
    return mpmath.mp.make_mpf(lo), mpmath.mp.make_mpf(hi)


def _guard(v: Any) -> Any:
    lo, hi = _ends(v)
    if not (mpmath.isfinite(lo) and mpmath.isfinite(hi)) or max(-lo, hi) > _LIMIT:
        raise _Skip
    return v


def _rational(q: Any) -> Any:
    return iv.mpf(int(q.p)) / iv.mpf(int(q.q))


def _reciprocal(v: Any) -> Any:
    lo, hi = _ends(v)
    if lo <= 0 <= hi:
        raise _Skip  # the box meets a pole
    return 1 / v


def _rational_power(base: Any, q: Any) -> Any:
    """Principal ``base ** q`` for a non-integer rational ``q``: real only for base >= 0."""
    lo, hi = _ends(base)
    if lo > 0:
        return base ** _rational(q)
    if lo == 0 and q > 0:  # monotone on [0, hi]
        top = _ends(iv.mpf(hi) ** _rational(q))[1] if hi > 0 else mpmath.mpf(0)
        return iv.mpf([0, top])
    raise _Skip


def _exp(v: Any) -> Any:
    lo, hi = _ends(v)
    if max(-lo, hi) > _EXP_LIMIT:
        raise _Skip
    return iv.exp(v)


def _log(v: Any) -> Any:
    if _ends(v)[0] <= 0:
        raise _Skip
    return iv.log(v)


def _abs(v: Any) -> Any:
    lo, hi = _ends(v)
    if lo >= 0:
        return v
    if hi <= 0:
        return -v
    return iv.mpf([0, max(-lo, hi)])


def _sign(v: Any) -> Any:
    lo, hi = _ends(v)
    if lo > 0:
        return iv.mpf(1)
    if hi < 0:
        return iv.mpf(-1)
    if lo == 0 and hi == 0:
        return iv.mpf(0)
    return iv.mpf([-1, 1])


_FUNCTIONS: dict[type, Callable[[Any], Any]] = {
    sympy.exp: _exp,
    sympy.log: _log,
    sympy.sin: lambda v: iv.sin(v),
    sympy.cos: lambda v: iv.cos(v),
    sympy.tan: lambda v: iv.sin(v) * _reciprocal(iv.cos(v)),
    sympy.cot: lambda v: iv.cos(v) * _reciprocal(iv.sin(v)),
    sympy.sec: lambda v: _reciprocal(iv.cos(v)),
    sympy.csc: lambda v: _reciprocal(iv.sin(v)),
    sympy.Abs: _abs,
    sympy.sign: _sign,
}


def _walk(expr: Any, env: dict[Any, Any]) -> Any:
    return _guard(_node(expr, env))


def _node(expr: Any, env: dict[Any, Any]) -> Any:
    if expr in env:
        return env[expr]
    if expr.is_Rational:
        return _rational(expr)
    if expr is sympy.pi:
        return iv.pi
    if expr is sympy.E:
        return iv.e
    if isinstance(expr, sympy.Add):
        total = iv.mpf(0)
        for arg in expr.args:
            total = _guard(total + _walk(arg, env))
        return total
    if isinstance(expr, sympy.Mul):
        product = iv.mpf(1)
        for arg in expr.args:
            product = _guard(product * _walk(arg, env))
        return product
    if isinstance(expr, sympy.Pow):
        return _power(expr.base, expr.exp, env)
    function = _FUNCTIONS.get(type(expr))
    if function is not None and len(expr.args) == 1:
        return function(_walk(expr.args[0], env))
    raise _Skip  # anything else: an unknown head, a free symbol, a Float, ...


def _power(base: Any, exponent: Any, env: dict[Any, Any]) -> Any:
    b = _walk(base, env)
    if exponent.is_Integer:
        n = int(exponent)
        if n == 0:
            return iv.mpf(1)  # SymPy's convention, 0**0 = 1, as the translator builds it
        magnitude = _guard(b ** abs(n))
        return magnitude if n > 0 else _reciprocal(magnitude)
    if exponent.is_Rational:
        return _rational_power(b, exponent)
    if _ends(b)[0] <= 0:
        raise _Skip  # a symbolic or irrational exponent is real only for a positive base
    return _exp(_guard(_walk(exponent, env) * iv.log(b)))


def _enclose(expr: Any, var: sympy.Symbol, box: Any) -> Box | None:
    try:
        return _ends(_walk(expr, {var: box}))
    except Exception:  # _Skip, or anything mpmath raises: no enclosure, never a verdict
        return None


def _point_box(point: Any) -> Any:
    return _rational(point)


def _neighbourhood(point: Any) -> Any:
    lo, hi = point - _HALF_WIDTH, point + _HALF_WIDTH
    return iv.mpf([_ends(_rational(lo))[0], _ends(_rational(hi))[1]])


def enclose(
    expr: sympy.Expr, var: sympy.Symbol, point: sympy.Rational, dps: int = DPS
) -> Box | None:
    """A rigorous ``dps``-digit enclosure of ``expr`` at ``point``, or None if not enclosable."""
    with _working_precision(dps):
        try:
            return _enclose(expr, var, _point_box(point))
        except Exception:  # e.g. a point that is not a SymPy Rational: no enclosure
            return None


def to_fraction(value: Any) -> Fraction:
    """The exact value of a finite mpf endpoint."""
    sign, man, exp, _ = value._mpf_
    magnitude: Fraction = Fraction(man) * Fraction(2) ** exp
    return -magnitude if sign else magnitude


# -- refutation ------------------------------------------------------------------------------


def _violated_on(c_kind: str, box: Box | None) -> bool:
    if box is None:
        return False
    hi = box[1]
    if c_kind == "positive":
        return bool(hi <= 0)
    if c_kind == "nonnegative":
        return bool(hi < 0)
    return False  # nonzero and the trig kinds only fail at isolated points


def _student_undefined(
    s: Translated, e: Translated, var: sympy.Symbol, point: Any, budget: Budget
) -> bool | None:
    """True if certified; None if the budget ran out."""
    near = _neighbourhood(point)
    for c in s.constraints:
        if budget.remaining() <= 0:
            return None
        if _violated_on(c.kind, _enclose(c.expr, var, near)):
            if budget.remaining() <= 0:
                return None
            # E must be defined on the whole neighbourhood; otherwise no constraint can help.
            return _enclose(e.expr, var, near) is not None
    return False


def _disjoint(a: Box, b: Box) -> bool:
    return bool(a[1] < b[0] or b[1] < a[0])


def _refute_at(
    s: Translated, e: Translated, var: sympy.Symbol, point: Any, budget: Budget
) -> VerdictReason | None:
    undefined = _student_undefined(s, e, var, point, budget)
    if undefined:
        return VerdictReason.STUDENT_UNDEFINED
    if undefined is None or budget.remaining() <= 0:
        return None
    box = _point_box(point)
    expected = _enclose(e.expr, var, box)
    if expected is None or budget.remaining() <= 0:
        return None
    student = _enclose(s.expr, var, box)
    if student is not None and _disjoint(student, expected):
        return VerdictReason.COUNTEREXAMPLE
    return None


def refute(
    s: Translated,
    e: Translated,
    var: sympy.Symbol,
    points: list[sympy.Rational],
    budget: Budget,
) -> VerdictReason | None:
    """``student_undefined`` or ``counterexample`` at the first certified point, else None.

    Every point must lie in the problem's domain D. Points that are not rational, or where an
    enclosure fails, are skipped. A spent budget returns None (no witness found).
    """
    with _working_precision():
        for point in points:
            if budget.remaining() <= 0:
                return None
            if not isinstance(point, sympy.Rational):
                continue
            reason = _refute_at(s, e, var, point, budget)
            if reason is not None:
                return reason
    return None


# -- points ----------------------------------------------------------------------------------


def _bound(text: str) -> Fraction | None:
    return None if text in ("-inf", "inf") else Fraction(text)


def sample_points(domain: Domain, seed: int = 0, n: int = 20) -> list[sympy.Rational]:
    """``n`` seeded rationals from D, plus each interval's closed finite ends and the midpoint
    of each bounded interval. Excluded points and open ends are never returned."""
    intervals = [
        (_bound(lo), _bound(hi), lo_kind == "closed", hi_kind == "closed")
        for lo, hi, lo_kind, hi_kind in domain.intervals
    ]
    excluded = {Fraction(p) for p in domain.exclude}

    def inside(q: Fraction) -> bool:
        if q in excluded:
            return False
        for lo, hi, lo_closed, hi_closed in intervals:
            above = lo is None or q > lo or (q == lo and lo_closed)
            below = hi is None or q < hi or (q == hi and hi_closed)
            if above and below:
                return True
        return False

    structured: list[Fraction] = []
    for lo, hi, lo_closed, hi_closed in intervals:
        if lo is not None and lo_closed:
            structured.append(lo)
        if hi is not None and hi_closed:
            structured.append(hi)
        if lo is not None and hi is not None:
            structured.append((lo + hi) / 2)

    rng = random.Random(seed)
    drawn: list[Fraction] = []
    for _ in range(50 * n):
        if len(drawn) >= n:
            break
        lo, hi, _, _ = intervals[rng.randrange(len(intervals))]
        if lo is not None and hi is not None:
            q = lo + (hi - lo) * Fraction(rng.randint(1, 999), 1000)
        elif lo is not None:
            q = lo + Fraction(rng.randint(1, 10_000), 1000)
        elif hi is not None:
            q = hi - Fraction(rng.randint(1, 10_000), 1000)
        else:
            q = Fraction(rng.randint(-10_000, 10_000), 1000)
        if q not in drawn and q not in structured:
            drawn.append(q)

    points = [q for q in dict.fromkeys(structured + drawn) if inside(q)]
    return [sympy.Rational(q.numerator, q.denominator) for q in points]


_RESOLUTIONS = (3, 6, 9, 12, 18, 30, 45, 60)


def _strictly_inside(p: Any, interval: sympy.Interval) -> bool:
    return (interval.start < p) is sympy.true and (p < interval.end) is sympy.true


def rational_inside(interval: sympy.Interval) -> sympy.Rational | None:
    """An exact rational strictly inside ``interval``, verified exactly, or None (owner R17).

    Finite ends are bracketed by rationals at 10^-3, refined to 10^-60; an infinite end is
    replaced by the finite end -/+ 1, moved to an integer toward the inside.
    """
    try:
        a, b = interval.start, interval.end
        if a is sympy.S.NegativeInfinity and b is sympy.S.Infinity:
            candidates = [sympy.S.Zero]
        elif a is sympy.S.NegativeInfinity:
            candidates = [sympy.floor(b) - 1]
        elif b is sympy.S.Infinity:
            candidates = [sympy.ceiling(a) + 1]
        else:
            candidates = []
            for k in _RESOLUTIONS:
                scale = sympy.Integer(10) ** k
                lo, hi = sympy.floor(a * scale), sympy.ceiling(b * scale)
                if lo.is_Integer and hi.is_Integer:
                    candidates.append((lo + hi) / (2 * scale))
        for p in candidates:
            if p.is_Rational and _strictly_inside(p, interval):
                return sympy.Rational(p)
    except Exception:  # an end SymPy cannot round or compare: no point, so the caller abstains
        return None
    return None
