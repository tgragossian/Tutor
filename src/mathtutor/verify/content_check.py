"""Offline math check of the content bundle (R1). Run by CI and the Docker build, never by the app.

``python -m mathtutor.verify.content_check [path]`` prints ``ok: N problems`` (exit 0) or one
``<id>: <field>: <reason>`` line per defect (exit 1). It imports SymPy, so the web process must
never import this module.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import sympy
from pydantic import JsonValue

from mathtutor.content.loader import ContentError, LoadedContent, load_bundle
from mathtutor.content.schema import (
    ChoiceAnswer,
    Domain,
    ExpressionAnswer,
    NumericAnswer,
    Problem,
)
from mathtutor.domain import AnswerKind, VerdictStatus
from mathtutor.verify.check import check
from mathtutor.verify.equivalence import Budget, equivalent, to_sympy_set, violation_set
from mathtutor.verify.latex_rules import unparenthesized_function
from mathtutor.verify.translate import (
    VARIABLE_ASSUMPTIONS,
    Rejected,
    TranslateContext,
    Translated,
    translate,
)
from mathtutor.verify.types import CheckRequest, FormatIssue, SubmittedAnswer, Verdict

DEFAULT_PATH = Path("content/compiled/problems.json")
_PROBLEM_SECONDS = 30.0
_GRADE_SECONDS = 10.0
_ALL_REALS = Domain()


def _translated(tree: JsonValue, variable: str) -> Translated | str:
    result = translate(tree, TranslateContext(variable))
    if isinstance(result, Rejected):
        return f"does not translate ({result.code}: {result.detail})"
    return result


def _parens_error(field: str, latex: str) -> str | None:
    """R22 on authored LaTeX: the same rule that rejects student input."""
    bare = unparenthesized_function(latex)
    return None if bare is None else f"{field}: function input needs parentheses ({bare})"


def _defined_at(tree: Translated, var: sympy.Symbol, point: sympy.Rational) -> bool | None:
    """Whether the expected answer has a real, finite value at ``point`` (None: undecided)."""
    try:
        value = sympy.simplify(tree.expr.subs(var, point))
    except Exception:
        return None
    if value.has(sympy.zoo, sympy.nan, sympy.oo, -sympy.oo):
        return False
    real, finite = value.is_extended_real, value.is_finite
    if real is False:
        return False
    if real is True and finite is True:
        return True
    return None


def _endpoint_checks(domain: Domain, tree: Translated, var: sympy.Symbol) -> list[str]:
    """Thomas's rule for authored intervals: infinite ends are open; a finite end is closed
    exactly when the expected answer is defined there (plug it in), else open. Closed ends
    where the answer is undefined are already reported as "undefined on domain"."""
    errors: list[str] = []
    for i, (lo, hi, lo_kind, hi_kind) in enumerate(domain.intervals):
        for end, kind, side in ((lo, lo_kind, "lower"), (hi, hi_kind, "upper")):
            if end in ("-inf", "inf") or kind == "closed":
                continue
            if _defined_at(tree, var, sympy.Rational(end)) is True:
                errors.append(
                    f"answer.domain: intervals[{i}] {side} end {end} should be closed: "
                    "the expected answer is defined there"
                )
    return errors


def _self_checks(answer: ExpressionAnswer | NumericAnswer, budget: Budget) -> list[str]:
    """The expected answer translates, equals itself, and is defined on its whole domain."""
    bare = _parens_error("answer.latex", answer.latex)
    if bare is not None:
        return [bare]
    tree = _translated(answer.mathjson, answer.variable)
    if isinstance(tree, str):
        return [f"answer.latex: {tree}"]
    numeric = isinstance(answer, NumericAnswer)
    domain = _ALL_REALS if numeric else answer.domain
    var = sympy.Symbol(answer.variable, **VARIABLE_ASSUMPTIONS)
    if numeric and tree.expr.free_symbols:
        return [f"answer.latex: numeric answer is not constant: {tree.expr}"]
    errors: list[str] = []
    try:
        region = to_sympy_set(domain)
    except Exception as error:
        return [f"answer.domain: domain unprovable ({error})"]
    for constraint in tree.constraints:
        try:
            bad = violation_set(constraint, var, region, budget)
        except Exception as error:  # DomainUnproven, budget spent, or SymPy failure: abstain
            errors.append(f"answer.domain: domain unprovable ({constraint.kind}: {error})")
            continue
        if bad.is_empty is not True:
            errors.append(f"answer.domain: expected answer undefined on domain at {bad}")
    if not numeric and not answer.strict_domain:
        errors += _endpoint_checks(domain, tree, var)
    strict = False if numeric else answer.strict_domain
    verdict = equivalent(tree, tree, domain, strict, var, budget)
    if not (isinstance(verdict, Verdict) and verdict.status == VerdictStatus.CORRECT):
        errors.append("answer.latex: not provably equal to itself")
    return list(dict.fromkeys(errors))


def _choice_checks(answer: ChoiceAnswer, budget: Budget) -> list[str]:
    errors: list[str] = []
    trees: dict[str, Translated] = {}
    for i, choice in enumerate(answer.choices):
        bare = _parens_error(f"answer.choices[{i}].latex", choice.latex)
        if bare is not None:
            errors.append(bare)
            continue
        tree = _translated(choice.mathjson, "x")
        if isinstance(tree, str):
            errors.append(f"answer.choices[{i}].latex: {tree}")
        else:
            trees[choice.id] = tree
    correct = trees.get(answer.correct)
    if correct is None:
        return errors
    var = sympy.Symbol("x", **VARIABLE_ASSUMPTIONS)
    for i, choice in enumerate(answer.choices):
        other = trees.get(choice.id)
        if choice.id == answer.correct or other is None:
            continue
        verdict = equivalent(other, correct, _ALL_REALS, False, var, budget)
        if isinstance(verdict, Verdict) and verdict.status == VerdictStatus.CORRECT:
            errors.append(
                f"answer.choices[{i}]: choice {choice.id} is provably equal to the correct "
                f"choice {answer.correct}"
            )
    return errors


def _misconception_checks(problem: Problem) -> list[str]:
    errors: list[str] = []
    spec = problem.answer
    for i, text in enumerate(problem.misconceptions):
        field = f"misconceptions[{i}]"
        head = text.split("  #")[0].strip()
        if isinstance(spec, ChoiceAnswer):
            if head not in {c.id for c in spec.choices}:
                errors.append(f"{field}: {head!r} is not a choice id")
                continue
            submitted = SubmittedAnswer(AnswerKind.CHOICE, None, "", head)
        else:
            trees = problem.misconceptions_mathjson
            tree = trees[i] if trees is not None else None
            bare = _parens_error(field, head)
            if bare is not None:
                errors.append(bare)
                continue
            if tree is None:  # the compiler could not parse it: skipped by design
                continue
            submitted = SubmittedAnswer(AnswerKind(spec.kind), tree, head, None)
        outcome = check(CheckRequest(spec, submitted), deadline_s=_GRADE_SECONDS).outcome
        if isinstance(outcome, FormatIssue):
            errors.append(f"{field}: misconception is not gradable: {outcome.code}")
            continue
        if isinstance(outcome, Verdict) and outcome.status == VerdictStatus.CORRECT:
            errors.append(f"{field}: graded correct against the expected answer")
    return errors


def check_bundle(content: LoadedContent) -> list[str]:
    """Every defect, as ``<id>: <field>: <reason>`` lines, in problem order."""
    lines: list[str] = []
    for problem in content.bundle.problems:
        budget = Budget(time.monotonic() + _PROBLEM_SECONDS)
        answer = problem.answer
        if isinstance(answer, ChoiceAnswer):
            found = _choice_checks(answer, budget)
        else:
            found = _self_checks(answer, budget)
        found += _misconception_checks(problem)
        lines += [f"{problem.id}: {line}" for line in found]
    return lines


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else DEFAULT_PATH
    try:
        content = load_bundle(path)
    except ContentError as error:
        print(error)
        return 1
    errors = check_bundle(content)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"ok: {len(content.bundle.problems)} problems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
