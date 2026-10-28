"""Help cases and retrieval queries: strict JSONL rows, review state and split checks.

Files live under ``<root>/evals/help/{cases,retrieval}/<split>.jsonl``. Only the ``dev`` and
``holdout`` splits exist here; nothing in C1 reads a ``final`` split (02-gates).
Every drafted row starts ``reviewed_by: needs_review``; the runner refuses such rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from mathtutor.content.schema import ChoiceAnswer, Problem
from mathtutor.help.context import Confusion, HelpType
from mathtutor.help.generator import MISTAKE_TYPES, MistakeType

SPLITS: tuple[str, ...] = ("dev", "holdout")
Split = Literal["dev", "holdout"]
CATEGORIES: tuple[str, ...] = (
    "mistaken_reasoning",
    "nearly_right",
    "tell_me_answer",
    "easy_l1_trap",
    "out_of_scope",
    "ordinary",
)
KNOWN_ERROR = "known_error"
NO_EVIDENCE = "no_evidence"
NEEDS_REVIEW = "needs_review"
REVIEWERS = frozenset({"tg"})
EVALS_DIR = Path("evals") / "help"
HOLDOUT_MIN_PROBLEMS = 7
TOPICS = 3


class _Row(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class HelpCase(_Row):
    """One help request on a bank problem. ``attempts`` are the student's LaTeX, oldest first
    (a choice id for choice problems); each is a wrong attempt. ``withhold_sections`` removes
    whole sections (``"3.6"``) or chapters (``"3"``) from the corpus for this case only, to
    simulate missing evidence. ``note`` tells the reviewer and the judge what the attempt
    shows; it never reaches the help prompt."""

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,40}$")
    split: Split
    problem_id: str
    help_type: HelpType
    attempts: list[str] = Field(max_length=6)
    confusion_id: str | None
    hint_level: int = Field(ge=0, le=3)
    # R35: a hint with attempts is the first hint on the latest attempt, so the model names its
    # mistake type. ``prior_hints``: hints each type already had on this problem; the right type
    # gives ``hint_level`` = its prior count + 1. ``expect_mistake_type`` is the reviewer's label.
    expect_mistake_type: MistakeType | None = None
    prior_hints: dict[str, int] = Field(default_factory=dict)
    start_step: int = Field(default=1, ge=1, le=2)  # level 0: 1 rule, 2 concrete setup
    tags: frozenset[str]
    expect_abstain: bool
    withhold_sections: list[str] = Field(default_factory=list)
    note: str = Field(min_length=1, max_length=600)
    reviewed_by: str = Field(min_length=1)

    @property
    def category(self) -> str:
        return next(t for t in self.tags if t in CATEGORIES)

    @property
    def known_error(self) -> bool:
        return KNOWN_ERROR in self.tags

    @model_validator(mode="after")
    def _rules(self) -> HelpCase:
        cats = [t for t in self.tags if t in CATEGORIES]
        if len(cats) != 1:
            raise ValueError(f"exactly one category tag of {CATEGORIES} is required")
        if (self.help_type == "explain") != (self.confusion_id is not None):
            raise ValueError("explain cases (and only they) need a confusion_id")
        if (cats[0] == "out_of_scope") != self.expect_abstain:
            raise ValueError("out_of_scope cases (and only they) expect an abstention")
        if self.withhold_sections and cats[0] != "out_of_scope":
            raise ValueError("withhold_sections is only for out_of_scope cases")
        if self.known_error and (not self.attempts or self.help_type == "explain"):
            raise ValueError("known_error needs an attempt and a hint or feedback request")
        if self.help_type == "hint" and (self.hint_level == 0) != (not self.attempts):
            raise ValueError("a hint is level 0 exactly when there is no wrong attempt yet")
        classifies = self.help_type == "hint" and bool(self.attempts)
        if classifies != (self.expect_mistake_type is not None):
            raise ValueError("expect_mistake_type is set exactly on hint cases with attempts")
        if self.start_step != 1 and (self.help_type != "hint" or self.hint_level != 0):
            raise ValueError("start_step 2 is only for level-0 hint cases")
        if self.prior_hints and not classifies:
            raise ValueError("prior_hints is only for hint cases with attempts")
        if not set(self.prior_hints) <= set(MISTAKE_TYPES):
            raise ValueError(f"prior_hints keys are mistake types {MISTAKE_TYPES}")
        if any(not 0 <= n <= 2 for n in self.prior_hints.values()):
            raise ValueError("prior_hints counts are 0-2")
        if classifies and self.expect_mistake_type is not None:
            expected = self.prior_hints.get(self.expect_mistake_type, 0) + 1
            if expected != self.hint_level:
                raise ValueError("hint_level must be prior_hints[expect_mistake_type] + 1")
        if cats[0] in ("mistaken_reasoning", "nearly_right") and not self.known_error:
            raise ValueError(f"{cats[0]} cases are known_error cases")
        return self


class RetrievalQuery(_Row):
    """A book question with the chunk ids that answer it. ``section`` is the query's home
    section; splits are grouped by it."""

    query_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,40}$")
    split: Split
    section: str = Field(pattern=r"^\d+\.\d+$")
    text: str = Field(min_length=3, max_length=500)
    notation: Literal["words", "latex", "mixed"]
    relevant_ids: list[str] = Field(min_length=1, max_length=6)
    reviewed_by: str = Field(min_length=1)


def split_file(root: Path, kind: Literal["cases", "retrieval"], split: str) -> Path:
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; C1 reads only {SPLITS}")
    return root / EVALS_DIR / kind / f"{split}.jsonl"


def _rows(path: Path) -> list[tuple[int, dict[str, object]]]:
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            data = json.loads(line)
            if not isinstance(data, dict):
                raise ValueError(f"{path.name}:{n}: expected an object")
            rows.append((n, data))
    return rows


def _load[T: _Row](path: Path, split: str, model: type[T], key: str) -> list[T]:
    out: list[T] = []
    seen: set[str] = set()
    for n, data in _rows(path):
        try:
            row = model.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"{path.name}:{n}: {exc.errors()[0]['msg']}") from None
        if getattr(row, "split") != split:  # noqa: B009
            raise ValueError(f"{path.name}:{n}: split is not {split!r}")
        ident = str(getattr(row, key))
        if ident in seen:
            raise ValueError(f"{path.name}:{n}: duplicate {key} {ident}")
        seen.add(ident)
        out.append(row)
    return out


def load_cases(path: Path, split: str) -> list[HelpCase]:
    return _load(path, split, HelpCase, "case_id")


def load_queries(path: Path, split: str) -> list[RetrievalQuery]:
    return _load(path, split, RetrievalQuery, "query_id")


def load_split(root: Path, split: str) -> tuple[list[HelpCase], list[RetrievalQuery]]:
    cases = load_cases(split_file(root, "cases", split), split)
    return cases, load_queries(split_file(root, "retrieval", split), split)


def unreviewed(items: list[HelpCase] | list[RetrievalQuery]) -> list[str]:
    """Ids of rows not yet signed off by an approved reviewer."""
    out = []
    for item in items:
        if item.reviewed_by not in REVIEWERS:
            out.append(item.case_id if isinstance(item, HelpCase) else item.query_id)
    return out


def confusion_label(
    case: HelpCase, problem: Problem, confusions: dict[str, list[Confusion]]
) -> str | None:
    if case.confusion_id is None:
        return None
    for c in confusions.get(problem.topic, []):
        if c.id == case.confusion_id:
            return c.label
    raise ValueError(f"{case.case_id}: unknown confusion {case.confusion_id}")


def check_bank(
    cases: list[HelpCase], problems: dict[str, Problem], confusions: dict[str, list[Confusion]]
) -> list[str]:
    """Problems exist, confusion ids belong to the problem's topic, choice attempts are wrong
    choice ids."""
    errors: list[str] = []
    for case in cases:
        problem = problems.get(case.problem_id)
        if problem is None:
            errors.append(f"{case.case_id}: unknown problem {case.problem_id}")
            continue
        try:
            confusion_label(case, problem, confusions)
        except ValueError as exc:
            errors.append(str(exc))
        answer = problem.answer
        if isinstance(answer, ChoiceAnswer):
            ids = {c.id for c in answer.choices}
            for attempt in case.attempts:
                if attempt not in ids:
                    errors.append(f"{case.case_id}: {attempt!r} is not a choice id")
                elif attempt == answer.correct:
                    errors.append(f"{case.case_id}: attempt is the correct choice")
    return errors


def check_grouping(
    dev: list[HelpCase], holdout: list[HelpCase], problems: dict[str, Problem]
) -> list[str]:
    """02-gates: grouped by problem; the holdout covers all 3 topics and >= 7 problems."""
    errors: list[str] = []
    dev_ids, hold_ids = {c.problem_id for c in dev}, {c.problem_id for c in holdout}
    for pid in sorted(dev_ids & hold_ids):
        errors.append(f"problem {pid} is in both splits")
    case_ids = [c.case_id for c in dev + holdout]
    if len(case_ids) != len(set(case_ids)):
        errors.append("a case_id is used twice across splits")
    topics = {problems[p].topic for p in hold_ids if p in problems}
    if len(topics) < TOPICS:
        errors.append(f"holdout covers {len(topics)} topics; needs all {TOPICS} topics")
    if len(hold_ids) < HOLDOUT_MIN_PROBLEMS:
        errors.append(f"holdout uses {len(hold_ids)} problems; needs >= {HOLDOUT_MIN_PROBLEMS}")
    return errors


def check_query_grouping(dev: list[RetrievalQuery], holdout: list[RetrievalQuery]) -> list[str]:
    """Retrieval splits are grouped by home section: no section on both sides."""
    both = {q.section for q in dev} & {q.section for q in holdout}
    errors = [f"section {s} has queries in both splits" for s in sorted(both)]
    ids = [q.query_id for q in dev + holdout]
    if len(ids) != len(set(ids)):
        errors.append("a query_id is used twice across splits")
    return errors
