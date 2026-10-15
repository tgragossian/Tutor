"""The verifier's single entry point (spec 02, spec 04). Runs only in verifier workers."""

from __future__ import annotations

import logging
import os
import time
from decimal import Decimal
from fractions import Fraction

import sympy
from pydantic import JsonValue

from mathtutor import __version__
from mathtutor.content.schema import Answer, ChoiceAnswer, Decimals, Domain, NumericAnswer
from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify.equivalence import Budget, Gap, equivalent, to_sympy_set
from mathtutor.verify.numeric import round_half_even, round_matches, rounded_cell
from mathtutor.verify.precheck import precheck
from mathtutor.verify.refute import (
    enclose,
    rational_inside,
    refute,
    sample_points,
    to_fraction,
)
from mathtutor.verify.structure import check_structure
from mathtutor.verify.translate import (
    VARIABLE_ASSUMPTIONS,
    Rejected,
    TranslateContext,
    Translated,
    translate,
)
from mathtutor.verify.types import CheckRequest, CheckResult, FormatIssue, SubmittedAnswer, Verdict

VERIFIER_VERSION: str = f"{__version__}+{os.environ.get('MATHTUTOR_GIT_SHA', 'dev')}"

log = logging.getLogger(__name__)

_CORRECT, _INCORRECT, _UNABLE = (
    VerdictStatus.CORRECT,
    VerdictStatus.INCORRECT,
    VerdictStatus.UNABLE_TO_VERIFY,
)
_CHOICE_MATCH = Verdict(_CORRECT, VerdictReason.CHOICE_MATCH, Method.EXACT)
_CHOICE_MISMATCH = Verdict(_INCORRECT, VerdictReason.CHOICE_MISMATCH, Method.EXACT)
_ROUNDED_MATCH = Verdict(_CORRECT, VerdictReason.ROUNDED_MATCH, Method.ROUNDING)
_ROUNDED_MISMATCH = Verdict(_INCORRECT, VerdictReason.ROUNDED_MISMATCH, Method.ROUNDING)
_UNDEFINED_ON_DOMAIN = Verdict(_INCORRECT, VerdictReason.UNDEFINED_ON_DOMAIN, Method.DOMAIN)
_DOMAIN_UNPROVEN = Verdict(_UNABLE, VerdictReason.DOMAIN_UNPROVEN, Method.DOMAIN)
_NOT_PROVEN = Verdict(_UNABLE, VerdictReason.NOT_PROVEN, Method.NONE)
_TIMEOUT = Verdict(_UNABLE, VerdictReason.TIMEOUT, Method.NONE)
_INTERNAL_ERROR = Verdict(_UNABLE, VerdictReason.INTERNAL_ERROR, Method.NONE)

# Exact numeric answers are constants: their domain is all of ℝ (spec 04 "numeric").
_CONSTANT_DOMAIN = Domain(intervals=[("-inf", "inf", "open", "open")])


class _ContentBug(Exception):
    """The expected answer cannot be graded against (task 6's content check prevents it)."""


def _expected(spec: NumericAnswer | Answer, ctx: TranslateContext) -> Translated:
    assert not isinstance(spec, ChoiceAnswer)
    expected = translate(spec.mathjson, ctx)
    if isinstance(expected, Rejected):
        raise _ContentBug(f"expected answer does not translate: {expected.code} {expected.detail}")
    return expected


def _abstain(budget: Budget, verdict: Verdict) -> Verdict:
    """An abstention, reported as a timeout when the budget is spent."""
    return _TIMEOUT if budget.remaining() <= 0 else verdict


_ROUNDING_DPS = (60, 120, 240)


def _certified_cell(expr: sympy.Expr, decimals: int, budget: Budget) -> int | None:
    """The rounding cell of an irrational constant, certified by enclosures (owner R21)."""
    for dps in _ROUNDING_DPS:
        if budget.remaining() <= 0:
            return None
        box = enclose(expr, sympy.Symbol("_unused"), sympy.S.Zero, dps=dps)
        if box is None:
            return None
        cell = rounded_cell(to_fraction(box[0]), to_fraction(box[1]), decimals)
        if cell is not None:
            return cell
    return None


def _grade_rounding(spec: NumericAnswer, literal: str, decimals: int, budget: Budget) -> Verdict:
    """Spec 02 rounding rule: exact for a rational expected value; otherwise certified (R21)."""
    expr = _expected(spec, TranslateContext(spec.variable)).expr
    value = expr.doit()
    if value.free_symbols:
        raise _ContentBug(f"expected value for a decimals answer is not constant: {value}")
    student = Decimal(literal)
    if isinstance(value, sympy.Rational):
        matches = round_matches(value, student, decimals)
    else:
        cell = _certified_cell(expr, decimals, budget)
        if cell is None:
            return _abstain(budget, _NOT_PROVEN)
        matches = cell == round_half_even(Fraction(student), decimals)
    return _ROUNDED_MATCH if matches else _ROUNDED_MISMATCH


def _certify_gap(
    gap: Gap,
    s: Translated,
    e: Translated,
    var: sympy.Symbol,
    domain: Domain,
    budget: Budget,
) -> Verdict:
    """A Gap is only a hint: grade it incorrect only with a certified point inside it (R17)."""
    if budget.remaining() <= 0:
        return _TIMEOUT
    point = rational_inside(gap.interval)
    if point is None or to_sympy_set(domain).contains(point) is not sympy.true:
        return _DOMAIN_UNPROVEN
    if refute(s, e, var, [point], budget) == VerdictReason.STUDENT_UNDEFINED:
        return _UNDEFINED_ON_DOMAIN
    return _abstain(budget, _DOMAIN_UNPROVEN)


def _grade_symbolic(spec: Answer, tree: JsonValue, budget: Budget) -> Verdict | FormatIssue:
    """Spec 04 steps 1-4 for expressions and exact numeric answers."""
    assert not isinstance(spec, ChoiceAnswer)
    ctx = TranslateContext(spec.variable)
    expected = _expected(spec, ctx)
    student = translate(tree, ctx)
    if isinstance(student, Rejected):
        return FormatIssue(student.code, student.detail)
    if isinstance(spec, NumericAnswer):
        domain, strict = _CONSTANT_DOMAIN, False
    else:
        domain, strict = spec.domain, spec.strict_domain
    var = sympy.Symbol(spec.variable, **VARIABLE_ASSUMPTIONS)
    result = equivalent(student, expected, domain, strict, var, budget)
    if isinstance(result, Verdict):
        return _abstain(budget, result) if result.status == _UNABLE else result
    if isinstance(result, Gap):
        return _certify_gap(result, student, expected, var, domain, budget)
    if budget.remaining() <= 0:
        return _TIMEOUT
    reason = refute(student, expected, var, sample_points(domain), budget)
    if reason is not None:
        return Verdict(_INCORRECT, reason, Method.REFUTATION)
    return _abstain(budget, _NOT_PROVEN)


def _decimal_literal(tree: JsonValue) -> str | None:
    if isinstance(tree, dict) and len(tree) == 1 and isinstance(tree.get("num"), str):
        literal = tree["num"]
        assert isinstance(literal, str)
        return literal
    return None


def _grade(spec: Answer, answer: SubmittedAnswer, budget: Budget) -> Verdict | FormatIssue:
    if isinstance(spec, ChoiceAnswer):
        issue = precheck(answer, spec)
        if issue is not None:
            return issue
        return _CHOICE_MATCH if answer.choice_id == spec.correct else _CHOICE_MISMATCH
    tree = answer.mathjson
    if tree is not None:  # None is reported as `empty` by precheck
        issue = check_structure(tree)
        if issue is not None:
            return issue
    issue = precheck(answer, spec)
    if issue is not None:
        return issue
    literal = _decimal_literal(tree)
    if isinstance(spec, NumericAnswer) and isinstance(spec.precision, Decimals) and literal:
        return _grade_rounding(spec, literal, spec.precision.decimals, budget)
    return _grade_symbolic(spec, tree, budget)


def check(req: CheckRequest, deadline_s: float = 3.0) -> CheckResult:
    """Grade one submission. Never raises, except ValueError for a kind mismatch (client bug).

    ``deadline_s`` is a soft budget checked between steps; the pool enforces the hard one.
    """
    started = time.monotonic()
    spec, answer = req.answer_spec, req.answer
    if answer.kind != spec.kind:
        raise ValueError(f"answer kind {answer.kind!s} does not match problem kind {spec.kind}")
    try:
        outcome = _grade(spec, answer, Budget(started + deadline_s))
    except _ContentBug as bug:
        log.error("%s (request %s)", bug, req.request_id)
        outcome = _INTERNAL_ERROR
    except Exception:
        log.exception("verifier failed (request %s)", req.request_id)
        outcome = _INTERNAL_ERROR
    worker_ms = int((time.monotonic() - started) * 1000)
    return CheckResult(outcome, VERIFIER_VERSION, worker_ms=worker_ms)
