"""Symbolic equivalence on a domain (spec 04 steps 1-2). Runs only in verifier workers.

``equivalent`` proves the formulas equal, then checks that the student's expression is
defined wherever the expected one is on D. It never guesses: anything SymPy cannot decide
is ``None`` (not proven, so task 5 tries to refute) or ``domain_unproven``.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

import sympy

from mathtutor.content.schema import Domain
from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify.translate import Constraint, Translated
from mathtutor.verify.types import Verdict

_CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
_DOMAIN_UNPROVEN = Verdict(
    VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.DOMAIN_UNPROVEN, Method.DOMAIN
)
_UNDEFINED_ON_DOMAIN = Verdict(
    VerdictStatus.INCORRECT, VerdictReason.UNDEFINED_ON_DOMAIN, Method.DOMAIN
)
_POLE_ON_DOMAIN = Verdict(VerdictStatus.INCORRECT, VerdictReason.POLE_ON_DOMAIN, Method.DOMAIN)


@dataclass
class Budget:
    """Soft time budget; ``deadline`` is a ``time.monotonic()`` value."""

    deadline: float

    def remaining(self) -> float:
        return self.deadline - time.monotonic()


@dataclass(frozen=True)
class Gap:
    """A subinterval of D where the student's expression is undefined and E is defined."""

    interval: sympy.Interval


class _Spent(Exception):
    """The budget ran out before a SymPy call."""


def _tick(budget: Budget) -> None:
    if budget.remaining() <= 0:
        raise _Spent


def _unlimited() -> Budget:
    return Budget(float("inf"))


# -- domains ---------------------------------------------------------------------------------


def _number(text: str) -> Any:
    if text == "-inf":
        return sympy.S.NegativeInfinity
    if text == "inf":
        return sympy.S.Infinity
    value = Fraction(text)
    return sympy.Rational(value.numerator, value.denominator)


def to_sympy_set(domain: Domain) -> sympy.Set:
    """The union of the domain's intervals minus its excluded points."""
    parts = [
        sympy.Interval(_number(lo), _number(hi), lo_kind == "open", hi_kind == "open")
        for lo, hi, lo_kind, hi_kind in domain.intervals
    ]
    whole = sympy.Union(*parts)
    if not domain.exclude:
        return whole
    return sympy.Complement(whole, sympy.FiniteSet(*(_number(p) for p in domain.exclude)))


def _proof_symbol(var: sympy.Symbol, D: sympy.Set) -> sympy.Symbol:
    """``var`` with the sign assumptions D implies, so e.g. ln(x²) = 2 ln x on (0, ∞)."""
    zero = sympy.S.Zero
    for assumption, superset in (
        ("positive", sympy.Interval.open(zero, sympy.oo)),
        ("negative", sympy.Interval.open(-sympy.oo, zero)),
        ("nonnegative", sympy.Interval(zero, sympy.oo)),
        ("nonpositive", sympy.Interval(-sympy.oo, zero)),
    ):
        if D.is_subset(superset) is True:
            return sympy.Symbol(var.name, real=True, **{assumption: True})
    if D.contains(zero) is sympy.false:
        return sympy.Symbol(var.name, real=True, nonzero=True)
    return var


# -- step 1: equality of the formulas --------------------------------------------------------

_STRATEGIES: tuple[Callable[[Any], Any], ...] = (
    lambda d: sympy.cancel(sympy.together(d)),
    sympy.simplify,
    sympy.trigsimp,
    lambda d: sympy.simplify(sympy.expand_trig(d)),
    lambda d: sympy.powsimp(d, force=False),
    sympy.radsimp,
)


def prove_equal(s: sympy.Expr, e: sympy.Expr, budget: Budget) -> bool:
    """True only if a spec 04 strategy reduces ``s - e`` to exactly 0."""
    if budget.remaining() <= 0:
        return False
    try:
        d = s - e
    except Exception:
        return False
    for strategy in _STRATEGIES:
        if budget.remaining() <= 0:
            return False
        try:
            result = strategy(d)
        except Exception:
            continue
        if result is sympy.S.Zero:
            return True
    return False


# -- step 2: the domain ----------------------------------------------------------------------


def _violated(c: Constraint) -> Any:
    """The condition (an expression meaning ``= 0``, or a relation) where ``c`` fails."""
    if c.kind == "nonzero":
        return c.expr
    if c.kind == "positive":
        return sympy.Le(c.expr, 0)
    if c.kind == "nonnegative":
        return sympy.Lt(c.expr, 0)
    if c.kind == "not_half_pi_odd":
        return sympy.cos(c.expr)
    return sympy.sin(c.expr)


class DomainUnproven(Exception):
    """``solveset`` cannot be trusted on a constraint (owner ruling R18)."""


def _has_real_root_form(expr: Any) -> bool:
    """``Abs`` or ``sign`` under a non-integer power: R14's real roots, which SymPy 1.14's
    ``solveset`` mis-solves (``|x|^(2/3) - 1 = 0`` gives EmptySet)."""
    return any(
        p.exp.is_integer is not True and p.base.has(sympy.Abs, sympy.sign)
        for p in expr.atoms(sympy.Pow)
    )


_FIXED_POINTS: tuple[int | Fraction, ...] = (
    *(0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 10, -10, 100, -100, 1000, -1000),
    *(Fraction(1, 2), Fraction(-1, 2), Fraction(1, 3), Fraction(-1, 3)),
    *(Fraction(3, 2), Fraction(-3, 2)),
)
_NEAR = (Fraction(1, 10), Fraction(1, 1000))
_RANDOM_PER_INTERVAL = 64
_SEED = 20261013


def _components(D: sympy.Set) -> list[sympy.Interval]:
    parts = D.args if isinstance(D, sympy.Union) else (D,)
    return [p for p in parts if isinstance(p, sympy.Interval)]


def _finite_bound(b: Any) -> Fraction | None:
    if not b.is_Rational:
        return None
    return Fraction(int(b.p), int(b.q))


def _sample_points(D: sympy.Set) -> list[Any]:
    """Deterministic rationals in D: fixed points, points near each finite bound and seeded
    pseudo-random points in every interval (at least 64 per interval)."""
    rng = random.Random(_SEED)
    candidates: list[Fraction] = [Fraction(p) for p in _FIXED_POINTS]
    for interval in _components(D):
        lo, hi = _finite_bound(interval.start), _finite_bound(interval.end)
        for bound in (b for b in (lo, hi) if b is not None):
            candidates += [bound, *(bound + d for d in _NEAR), *(bound - d for d in _NEAR)]
        low = lo if lo is not None else (hi - 200 if hi is not None else Fraction(-200))
        high = hi if hi is not None else low + 400
        for _ in range(_RANDOM_PER_INTERVAL):
            candidates.append(low + (high - low) * Fraction(rng.randint(1, 9999), 10000))
    points = []
    for value in dict.fromkeys(candidates):
        point = sympy.Rational(value.numerator, value.denominator)
        if D.contains(point) is sympy.true:
            points.append(point)
    return points


def _violated_at(c: Constraint, var: sympy.Symbol, point: Any) -> bool | None:
    """Whether ``c`` is violated at ``point``; None where undefined or undecided."""
    value = c.expr.subs(var, point)
    if value.is_finite is not True or value.is_extended_real is not True:
        return None
    holds = _holds_at(c, var, point)
    return None if holds is None else not holds


def _cross_check(
    c: Constraint, var: sympy.Symbol, D: sympy.Set, found: sympy.Set, budget: Budget
) -> None:
    """Raise DomainUnproven if a sample point disagrees with ``found`` (ruling R18)."""
    for point in _sample_points(D):
        _tick(budget)
        violated = _violated_at(c, var, point)
        if violated is None:
            continue
        member = found.contains(point)
        if member is not sympy.true and member is not sympy.false:
            raise DomainUnproven("membership undecided")
        if violated != (member is sympy.true):
            raise DomainUnproven(f"solveset disagrees with the constraint at {point}")


def violation_set(
    c: Constraint, var: sympy.Symbol, D: sympy.Set, budget: Budget | None = None
) -> sympy.Set:
    """The points of D where ``c`` is violated (``solveset`` intersected with D).

    ``solveset`` is untrusted (R18): real-root forms raise DomainUnproven without solving,
    and an empty, finite or interval answer is cross-checked at sample points of D.
    """
    budget = budget or _unlimited()
    if _has_real_root_form(c.expr):
        raise DomainUnproven("real-root form in a constraint")
    _tick(budget)
    found = sympy.Intersection(sympy.solveset(_violated(c), var, D), D)
    if found.is_empty is True or isinstance(found, sympy.FiniteSet | sympy.Interval | sympy.Union):
        _cross_check(c, var, D, found, budget)
    return found


def _holds_at(c: Constraint, var: sympy.Symbol, h: Any) -> bool | None:
    """Whether ``c`` holds exactly at ``h``; None when SymPy cannot decide."""
    value = c.expr.subs(var, h)
    if value.is_finite is not True:
        return None
    if c.kind == "positive":
        decided = value.is_positive
    elif c.kind == "nonnegative":
        decided = value.is_nonnegative
    else:
        if c.kind == "not_half_pi_odd":
            value = sympy.cos(value)
        elif c.kind == "not_pi_multiple":
            value = sympy.sin(value)
        zero = value.is_zero
        decided = None if zero is None else not zero
    return None if decided is None else bool(decided)


def _defined_at(
    constraints: tuple[Constraint, ...], var: sympy.Symbol, h: Any, budget: Budget
) -> bool | None:
    """True if every constraint holds at ``h``, False if one is violated, else None."""
    unknown = False
    for c in constraints:
        _tick(budget)
        holds = _holds_at(c, var, h)
        if holds is False:
            return False
        unknown = unknown or holds is None
    return None if unknown else True


_INFINITE = (sympy.S.Infinity, sympy.S.NegativeInfinity, sympy.S.ComplexInfinity)


def _hole(s: Any, e: Any, var: sympy.Symbol, h: Any, budget: Budget) -> bool | None:
    """True: removable at ``h``. False: a one-sided limit is infinite. None: undecided."""
    try:
        _tick(budget)
        target = e.subs(var, h)
        if target.is_finite is not True or target.is_extended_real is not True:
            return None
        for direction in ("+", "-"):
            _tick(budget)
            lim = sympy.limit(s, var, h, dir=direction)
            if lim in _INFINITE:
                return False
            if lim.is_finite is not True or lim.free_symbols or lim.has(sympy.Limit):
                return None
            if not prove_equal(lim, target, budget):
                return None
        return True
    except Exception:  # _Spent, or anything SymPy raises
        return None


def removable_at(
    s: sympy.Expr, e: sympy.Expr, var: sympy.Symbol, h: Any, budget: Budget | None = None
) -> bool:
    """Both one-sided limits of ``s`` at ``h`` exist, are finite and equal ``e`` at ``h``."""
    return _hole(s, e, var, h, budget or _unlimited()) is True


def _intervals(found: sympy.Set) -> list[sympy.Interval]:
    parts = found.args if isinstance(found, sympy.Union) else (found,)
    return [
        p for p in parts if isinstance(p, sympy.Interval) and p.measure.is_extended_positive is True
    ]


def _gap(found: sympy.Set, e: Translated, var: sympy.Symbol, budget: Budget) -> Gap | None:
    """The first subinterval of ``found`` where E is defined, if SymPy can show one."""
    for interval in _intervals(found):
        bad = []
        for c in e.constraints:
            _tick(budget)
            bad.append(violation_set(c, var, interval, budget))
        _tick(budget)
        rest = sympy.Complement(interval, sympy.Union(*bad)) if bad else interval
        if isinstance(rest, sympy.Interval | sympy.Union):
            pieces = _intervals(rest)
            if pieces:
                return Gap(pieces[0])
    return None


def _check_constraint(
    c: Constraint,
    s: Translated,
    e: Translated,
    D: sympy.Set,
    strict: bool,
    var: sympy.Symbol,
    budget: Budget,
) -> Verdict | Gap | None:
    """None when ``c`` costs nothing on D, else the verdict or Gap it forces."""
    if c in e.constraints:
        return None  # wherever the student fails c, E is undefined too
    _tick(budget)
    found = violation_set(c, var, D, budget)
    if found.is_empty is True:
        return None
    if isinstance(found, sympy.FiniteSet):
        for h in found.args:
            defined = _defined_at(e.constraints, var, h, budget)
            if defined is None:
                return _DOMAIN_UNPROVEN
            if not defined:
                continue
            if strict:
                return _UNDEFINED_ON_DOMAIN
            hole = _hole(s.expr, e.expr, var, h, budget)
            if hole is None:
                return _DOMAIN_UNPROVEN
            if not hole:
                return _POLE_ON_DOMAIN
        return None
    if isinstance(found, sympy.Interval | sympy.Union):
        gap = _gap(found, e, var, budget)
        if gap is not None:
            return gap
    return _DOMAIN_UNPROVEN


def _check_domain(
    s: Translated, e: Translated, D: sympy.Set, strict: bool, var: sympy.Symbol, budget: Budget
) -> Verdict | Gap:
    try:
        for c in s.constraints:
            outcome = _check_constraint(c, s, e, D, strict, var, budget)
            if outcome is not None:
                return outcome
    except Exception:  # _Spent, or anything SymPy raises: never a guess
        return _DOMAIN_UNPROVEN
    return _CORRECT


def equivalent(
    s: Translated,
    e: Translated,
    domain: Domain,
    strict: bool,
    var: sympy.Symbol,
    budget: Budget,
) -> Verdict | Gap | None:
    """Spec 04 steps 1-2: a Verdict, a Gap for task 5 to certify, or None (not proven)."""
    if budget.remaining() <= 0:
        return None
    try:
        D = to_sympy_set(domain)
        proof_var = _proof_symbol(var, D)
        s_expr, e_expr = s.expr, e.expr
        if proof_var is not var:
            s_expr, e_expr = s_expr.xreplace({var: proof_var}), e_expr.xreplace({var: proof_var})
    except Exception:
        return None
    if not prove_equal(s_expr, e_expr, budget):
        return None
    return _check_domain(s, e, D, strict, var, budget)
