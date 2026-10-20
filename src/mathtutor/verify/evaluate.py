"""Offline verifier evaluation (spec 08): metrics with Wilson intervals, gates, results JSON.

``python -m mathtutor.verify.evaluate --set dev|generated [--gate B [--draft]] [--out <json>]``
grades through a one-worker VerifierPool (3 s deadline); it imports SymPy-using modules and must
never be imported by the web process.
Exit 0 when every gate holds (or no gate was asked for), 1 otherwise. A dev gate is a release
check: every row needs an approved human reviewer. ``--draft`` measures unreviewed rows against
the same gates without that check, and its output is marked as never being a release result.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator

from mathtutor.content.loader import ContentError, LoadedContent, load_bundle
from mathtutor.content.schema import Answer, ChoiceAnswer
from mathtutor.domain import AnswerKind, FormatIssueCode, VerdictReason, VerdictStatus
from mathtutor.jsonio import loads_exact
from mathtutor.verify.check import check
from mathtutor.verify.pool import VerifierPool
from mathtutor.verify.types import (
    VERIFIER_VERSION,
    CheckRequest,
    CheckResult,
    FormatIssue,
    SubmittedAnswer,
    Verdict,
)

DEFAULT_CONTENT = Path("content/compiled/problems.json")
SET_PATHS = {
    "dev": Path("evals/verifier/human/dev.jsonl"),
    "generated": Path("evals/verifier/generated/mutations.jsonl"),
}
GRADE_DEADLINE_S = 3.0
LABELS = ("correct", "incorrect", "unsupported")
GATES_B: dict[str, float] = {
    "min_cases": 80,
    "fa_max": 0,
    "fr_max": 0.02,
    "coverage_min": 0.85,
    "generated_fa_max": 0,
}
# Format issues an `unsupported` label expects: notation, size, and partial (placeholder) input.
_UNSUPPORTED_ISSUES = {
    FormatIssueCode.UNSUPPORTED_NOTATION,
    FormatIssueCode.WRONG_DECIMAL_PLACES,
    FormatIssueCode.INPUT_TOO_LARGE,
    FormatIssueCode.EMPTY,
    FormatIssueCode.INCOMPLETE,
}
_ANSWER_ADAPTER: TypeAdapter[Any] = TypeAdapter(Answer)
# Spec 08 coverage minimums for the human dev set (task 9 table); `baseline` has no minimum.
CATEGORY_MIN: dict[str, int] = {
    "tricky": 15,
    "error": 20,
    "domain": 12,
    "near": 8,
    "partial": 6,
    "unsupported": 8,
    "resource": 5,
    "rounding": 6,
}
KNOWN_CATEGORIES = frozenset(CATEGORY_MIN) | {"baseline"}
# Human reviewers whose sign-off makes a dev row release-eligible. Never `pending`/`generated`.
APPROVED_REVIEWERS = frozenset({"tg"})

Rate = tuple[int, int]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes in n trials."""
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


_ANSWER_KEYS = {"mathjson", "latex", "choice_id"}


class Case(BaseModel):
    """One case row (spec 08). Strict: unknown keys and blank rationale/reviewer are errors."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    family: str = Field(min_length=1)
    problem_id: str | None = None
    inline_spec: dict[str, Any] | None = None
    answer: dict[str, Any]
    label: Literal["correct", "incorrect", "unsupported"]
    rationale: str
    reviewer: str
    # Spec 08 coverage bucket, copied from dev.src.yaml; required for a dev release gate.
    category: str | None = None
    # The authored input behind a browser capture: LaTeX set on the field, or keys typed.
    raw_latex: str | None = None
    raw_keys: list[str] | None = None

    @field_validator("rationale", "reviewer")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must be a non-empty string")
        return value

    @field_validator("answer")
    @classmethod
    def _known_answer_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(value) - _ANSWER_KEYS)
        if unknown:
            raise ValueError(f"unknown answer keys {unknown}")
        return value


@dataclass(frozen=True)
class CaseResult:
    id: str
    family: str
    label: str
    status: str  # correct | incorrect | unable_to_verify | format_issue
    reason: str
    method: str
    agrees: bool
    worker_ms: int


@dataclass
class Metrics:
    fa: Rate
    fr: Rate
    coverage: Rate
    abstain: dict[str, Rate]
    by_kind_reason_method: dict[str, int]
    # `unsupported` cases graded correct: a zero-tolerance accept (ruling R11).
    unsupported_accept: Rate = field(default=(0, 0))
    # Cases whose outcome matches the label; and verifier crashes (a bug, never an abstention).
    agreement: Rate = field(default=(0, 0))
    internal_errors: int = 0


def parse_cases(rows: list[dict[str, Any]]) -> list[Case]:
    cases: list[Case] = []
    for i, row in enumerate(rows, 1):
        where = f"case {i} ({row.get('id', '?')})"
        try:
            case = Case.model_validate(row)
            if (case.problem_id is None) == (case.inline_spec is None):
                raise ValueError("exactly one of problem_id or inline_spec is required")
        except ValidationError as error:
            details = "; ".join(
                f"{'.'.join(str(p) for p in e['loc']) or '(row)'}: {e['msg']}"
                for e in error.errors()
            )
            raise ValueError(f"{where}: {details}") from error
        except ValueError as error:
            raise ValueError(f"{where}: {error}") from error
        cases.append(case)
    ids = [c.id for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate case ids")
    return cases


def _rows(text: str, name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = loads_exact(line)
        except ValueError as error:
            raise ValueError(f"{name}:{number}: invalid JSON ({error})") from error
        if not isinstance(row, dict):
            raise ValueError(f"{name}:{number}: case must be a JSON object")
        rows.append(row)
    return rows


def load_cases(path: Path) -> list[Case]:
    return parse_cases(_rows(path.read_text(encoding="utf-8"), path.name))


def _spec_for(case: Case, content: LoadedContent) -> Any:
    if case.inline_spec is not None:
        try:
            return _ANSWER_ADAPTER.validate_python(case.inline_spec)
        except ValidationError as error:
            raise ValueError(f"{case.id}: invalid inline_spec: {error}") from error
    for problem in content.bundle.problems:
        if problem.id == case.problem_id:
            return problem.answer
    raise ValueError(f"{case.id}: unknown problem_id {case.problem_id!r}")


def _submitted(case: Case, spec: Any) -> SubmittedAnswer:
    kind = AnswerKind(spec.kind)
    choice = case.answer.get("choice_id") if isinstance(spec, ChoiceAnswer) else None
    mathjson = None if isinstance(spec, ChoiceAnswer) else case.answer.get("mathjson")
    return SubmittedAnswer(kind, mathjson, str(case.answer.get("latex", "")), choice)


def _agrees(label: str, outcome: Verdict | FormatIssue) -> bool:
    if isinstance(outcome, FormatIssue):
        return label == "unsupported" and outcome.code in _UNSUPPORTED_ISSUES
    if label == "correct":
        return outcome.status == VerdictStatus.CORRECT
    if label == "incorrect":
        return outcome.status == VerdictStatus.INCORRECT
    return False


def evaluate(
    cases: list[Case],
    content: LoadedContent,
    grade: Callable[[CheckRequest], CheckResult] | None = None,
) -> tuple[Metrics, list[CaseResult]]:
    """Grade every case. ``grade`` defaults to ``check`` in this process; the CLI passes a pool."""
    grade = grade or check
    results: list[CaseResult] = []
    breakdown: Counter[str] = Counter()
    for case in cases:
        spec = _spec_for(case, content)
        graded = grade(CheckRequest(spec, _submitted(case, spec), case.id))
        outcome = graded.outcome
        if isinstance(outcome, FormatIssue):
            status, reason, method = "format_issue", f"format:{outcome.code}", "none"
        else:
            status, reason, method = str(outcome.status), str(outcome.reason), str(outcome.method)
        breakdown[f"{spec.kind}|{reason}|{method}"] += 1
        results.append(
            CaseResult(
                case.id,
                case.family,
                case.label,
                status,
                reason,
                method,
                _agrees(case.label, outcome),
                graded.worker_ms,
            )
        )
    return _metrics(results, breakdown), results


def _metrics(results: list[CaseResult], breakdown: Counter[str]) -> Metrics:
    by_label = {label: [r for r in results if r.label == label] for label in LABELS}
    wrong, right = by_label["incorrect"], by_label["correct"]
    unsupported = by_label["unsupported"]
    graded_correct = str(VerdictStatus.CORRECT)
    abstain: dict[str, Rate] = {}
    for label, rows in by_label.items():
        no_verdict = [r for r in rows if r.status == "unable_to_verify"]
        if label != "unsupported":
            no_verdict += [r for r in rows if r.status == "format_issue"]
        abstain[label] = (len(no_verdict), len(rows))
    return Metrics(
        fa=(sum(r.status == graded_correct for r in wrong), len(wrong)),
        fr=(sum(r.status == "incorrect" for r in right), len(right)),
        coverage=(sum(r.status == graded_correct for r in right), len(right)),
        abstain=abstain,
        by_kind_reason_method=dict(sorted(breakdown.items())),
        unsupported_accept=(
            sum(r.status == graded_correct for r in unsupported),
            len(unsupported),
        ),
        agreement=(sum(r.agrees for r in results), len(results)),
        internal_errors=sum(r.reason == str(VerdictReason.INTERNAL_ERROR) for r in results),
    )


def dataset_failures(cases: list[Case], mode: str, *, draft: bool = False) -> list[str]:
    """Set-validity gates (review B-E1, B-E2), independent of what the verifier outputs.

    Generated: must not be empty. Dev: every label present, every row in a known category with
    each spec 08 minimum met, and (unless ``draft``) every row signed by an approved reviewer.
    """
    if not cases:
        return [f"empty {mode} set: no cases to evaluate"]
    if mode != "dev":
        return []
    failures: list[str] = []
    labels: Counter[str] = Counter(c.label for c in cases)
    failures += [f"no {label} cases in the dev set" for label in LABELS if not labels[label]]
    missing = [c.id for c in cases if c.category is None]
    if missing:
        failures.append(f"category missing on {len(missing)} rows: {', '.join(missing[:5])}")
    unknown = sorted({c.category for c in cases if c.category is not None} - KNOWN_CATEGORIES)
    if unknown:
        failures.append(f"unknown categories: {', '.join(unknown)}")
    counts = Counter(c.category for c in cases)
    for category, need in CATEGORY_MIN.items():
        if counts[category] < need:
            failures.append(f"category {category}: {counts[category]} cases (need {need})")
    if not draft:
        unreviewed = [c.id for c in cases if c.reviewer not in APPROVED_REVIEWERS]
        if unreviewed:
            failures.append(
                f"unreviewed: {len(unreviewed)} rows lack an approved reviewer "
                f"({', '.join(unreviewed[:5])}{', ...' if len(unreviewed) > 5 else ''})"
            )
    return failures


def gate_failures(
    metrics: Metrics, n_cases: int, mode: str, gates: dict[str, float] = GATES_B
) -> list[str]:
    """Which gates fail. The generated set is regression-only: zero false accepts, no min_cases."""
    failures: list[str] = []
    if metrics.fa[1] == 0:
        failures.append("no incorrect cases graded: FA 0 of 0 proves nothing")
    fa_max = gates["generated_fa_max"] if mode == "generated" else gates["fa_max"]
    if metrics.fa[0] > fa_max:
        failures.append(f"false accept: {metrics.fa[0]} of {metrics.fa[1]} (max {fa_max})")
    if metrics.unsupported_accept[0] > 0:
        k, n = metrics.unsupported_accept
        failures.append(f"unsupported input graded correct: {k} of {n} (max 0)")
    if metrics.internal_errors:
        failures.append(f"internal_error: {metrics.internal_errors} cases crashed the verifier")
    if mode == "generated" and metrics.agreement[0] < metrics.agreement[1]:
        k, n = metrics.agreement
        failures.append(f"regression: only {k} of {n} cases agree with their label")
    if mode == "dev":
        if n_cases < gates["min_cases"]:
            failures.append(f"min_cases: {n_cases} cases (need {int(gates['min_cases'])})")
        k, n = metrics.fr
        if n and k / n > gates["fr_max"]:
            failures.append(f"false reject: {k} of {n} exceeds {gates['fr_max']:.0%}")
        k, n = metrics.coverage
        if n == 0 or k / n < gates["coverage_min"]:
            failures.append(f"coverage: {k} of {n} is below {gates['coverage_min']:.0%}")
    return failures


def _rate(name: str, rate: Rate) -> str:
    k, n = rate
    lo, hi = wilson(k, n)
    if n and k == 0:
        return f"{name}: 0 of {n} (95% upper bound {hi:.1%})"
    pct = f"{k / n:.1%}, " if n else ""
    return f"{name}: {k} of {n} ({pct}95% Wilson {lo:.1%} to {hi:.1%})"


def render_summary(metrics: Metrics) -> str:
    lines = [
        _rate("FA (wrong accepted)", metrics.fa),
        _rate("FR (correct rejected)", metrics.fr),
        _rate("Supported coverage", metrics.coverage),
        _rate("Unsupported graded correct", metrics.unsupported_accept),
        _rate("Agreement with label", metrics.agreement),
    ]
    lines += [_rate(f"Abstain ({label})", rate) for label, rate in metrics.abstain.items()]
    lines += [f"  {key}: {count}" for key, count in metrics.by_kind_reason_method.items()]
    return "\n".join(lines)


def _rate_json(rate: Rate) -> dict[str, Any]:
    return {"k": rate[0], "n": rate[1], "wilson": list(wilson(*rate))}


def reviewed(cases: list[Case]) -> Rate:
    return (sum(c.reviewer in APPROVED_REVIEWERS for c in cases), len(cases))


def results_json(
    metrics: Metrics,
    results: list[CaseResult],
    set_name: str,
    sha: str,
    content_version: str,
    *,
    draft: bool = False,
    reviewed_rate: Rate = (0, 0),
) -> dict[str, Any]:
    return {
        "verifier_version": VERIFIER_VERSION,
        "content_version": content_version,
        "set": set_name,
        "set_sha256": sha,
        "draft": draft,
        "reviewed": {"k": reviewed_rate[0], "n": reviewed_rate[1]},
        "metrics": {
            "fa": _rate_json(metrics.fa),
            "fr": _rate_json(metrics.fr),
            "coverage": _rate_json(metrics.coverage),
            "unsupported_accept": _rate_json(metrics.unsupported_accept),
            "agreement": _rate_json(metrics.agreement),
            "internal_errors": metrics.internal_errors,
            "abstain": {label: _rate_json(rate) for label, rate in metrics.abstain.items()},
            "by_kind_reason_method": metrics.by_kind_reason_method,
        },
        "cases": [vars(r) for r in results],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mathtutor.verify.evaluate")
    parser.add_argument("--set", dest="set_name", choices=sorted(SET_PATHS), required=True)
    parser.add_argument("--gate", choices=["B"])
    parser.add_argument(
        "--draft", action="store_true", help="measure unreviewed rows; never a release result"
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--cases", type=Path, help="override the set's JSONL path")
    parser.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    path: Path = args.cases or SET_PATHS[args.set_name]
    if not path.is_file():
        print(f"cases file not found: {path}")
        return 1
    try:
        content = load_bundle(args.content)
        raw = path.read_bytes()
        cases = parse_cases(_rows(raw.decode("utf-8"), path.name))
        # Each case runs in a worker under the standard deadline: a pathological case becomes a
        # timeout abstention instead of hanging CI.
        pool = VerifierPool(size=1, deadline_s=GRADE_DEADLINE_S)
        try:
            metrics, results = evaluate(cases, content, grade=pool.submit)
        finally:
            pool.close()
    except (ContentError, ValueError, RuntimeError) as error:
        print(error)
        return 1
    sha = hashlib.sha256(raw).hexdigest()
    print(f"set: {args.set_name} ({len(cases)} cases, sha256 {sha[:12]}) {VERIFIER_VERSION}")
    print(render_summary(metrics))
    reviewed_rate = reviewed(cases)
    if args.draft:
        k, n = reviewed_rate
        print(f"DRAFT: {k} of {n} rows reviewed; this run is never a release result")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        payload = results_json(
            metrics,
            results,
            args.set_name,
            sha,
            content.bundle_version,
            draft=args.draft,
            reviewed_rate=reviewed_rate,
        )
        args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    if args.gate:
        failures = dataset_failures(cases, args.set_name, draft=args.draft)
        failures += gate_failures(metrics, len(cases), args.set_name)
        for failure in failures:
            print(f"GATE FAILED: {failure}")
        if failures:
            return 1
        if args.draft:
            print(f"gate {args.gate} (draft, not a release): metrics ok")
        else:
            print(f"gate {args.gate}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
