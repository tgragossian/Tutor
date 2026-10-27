"""Server-owned help context: what Claude is told about the problem and the attempts.

Never the answer: the correct LaTeX, the correct choice id and the review notes are not fields
of ``HelpContext`` and nothing here copies them. ``assemble_context`` and
``match_misconception`` are pure (no database); ``build_context`` adds the database read.
Web process only: no SymPy; misconceptions are graded through the verifier pool.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from mathtutor.application.practice import Pool
from mathtutor.content.schema import ChoiceAnswer, ExpressionAnswer, Problem, split_misconception
from mathtutor.domain import AnswerKind, VerdictStatus
from mathtutor.help.latex_parse import ParsedMath, parse_latex
from mathtutor.jsonio import loads_exact
from mathtutor.store.models import AttemptResult, SessionItem, Submission
from mathtutor.verify.types import CheckRequest, SubmittedAnswer, Verdict

HelpType = Literal["hint", "feedback", "explain"]

MAX_ATTEMPTS = 3
MAX_ATTEMPT_BYTES = 400
MATCH_DEADLINE_S = 3.0
MAX_MATCHES = 3
MAX_LABEL = 80
_CONFUSION_ID = re.compile(r"^[a-z_]{3,40}$")


@dataclass(frozen=True)
class AttemptLine:
    latex: str
    status: VerdictStatus


@dataclass(frozen=True)
class HelpContext:
    problem_id: str
    topic: str
    section: str
    statement: str
    answer_kind: AnswerKind
    attempts: list[AttemptLine]
    tries_used: int
    hint_level: int
    misconception_note: str | None
    variable: str


@dataclass(frozen=True)
class Confusion:
    id: str
    label: str


def misconception_note(entry: str) -> str | None:
    """The text after the two-space-hash separator of an authored misconception, if any."""
    return split_misconception(entry)[1]


def _head(entry: str) -> str:
    return split_misconception(entry)[0]


def _clip(latex: str) -> str:
    return latex.encode("utf-8")[:MAX_ATTEMPT_BYTES].decode("utf-8", errors="ignore")


def assemble_context(
    problem: Problem,
    attempts: list[AttemptLine],
    hint_level: int,
    misconception_note: str | None,
) -> HelpContext:
    """``attempts`` are oldest first, as submitted; the context lists the newest three first.

    ``tries_used`` here is an approximation (the count of incorrect attempts given) for callers
    without an item; ``build_context`` replaces it with the item's own counter.
    """
    answer = problem.answer
    recent = [AttemptLine(_clip(a.latex), a.status) for a in reversed(attempts[-MAX_ATTEMPTS:])]
    return HelpContext(
        problem_id=problem.id,
        topic=problem.topic,
        section=problem.source.section,
        statement=problem.statement,
        answer_kind=AnswerKind(answer.kind),
        attempts=recent,
        tries_used=sum(1 for a in attempts if a.status is VerdictStatus.INCORRECT),
        hint_level=hint_level,
        misconception_note=misconception_note,
        variable="x" if isinstance(answer, ChoiceAnswer) else answer.variable,
    )


def match_misconception(
    problem: Problem,
    latest: AttemptLine | None,
    chosen_choice: str | None,
    pool: Pool,
    *,
    clock: Callable[[], float] = time.monotonic,
) -> str | None:
    """The note of the first authored misconception the latest wrong attempt reproduces.

    Only an ``incorrect`` attempt is matched. Choice problems compare the chosen id; the
    others submit the attempt to the grading pool against each misconception as an expression
    answer, trying at most the first ``MAX_MATCHES`` and stopping at the first match. The
    ``MATCH_DEADLINE_S`` budget is soft: it is checked before each submit, because
    ``Pool.submit`` takes no deadline, so one slow call can overrun it. Busy, error, timeout
    or anything but ``correct`` is no match.
    """
    if latest is None or latest.status is not VerdictStatus.INCORRECT:
        return None
    answer = problem.answer
    if isinstance(answer, ChoiceAnswer):
        if chosen_choice is None:
            return None
        for entry in problem.misconceptions:
            if _head(entry) == chosen_choice:
                return misconception_note(entry)
        return None
    trees = problem.misconceptions_mathjson
    if not trees:
        return None
    parsed = parse_latex(latest.latex, variable=answer.variable)
    if not isinstance(parsed, ParsedMath) or parsed.foreign:
        return None
    started = clock()
    submitted = SubmittedAnswer(AnswerKind.EXPRESSION, parsed.tree, latest.latex, None)
    for entry, tree in list(zip(problem.misconceptions, trees, strict=True))[:MAX_MATCHES]:
        if tree is None:
            continue
        if clock() - started >= MATCH_DEADLINE_S:
            return None
        spec = ExpressionAnswer(
            kind="expression",
            latex=_head(entry),
            mathjson=tree,
            variable=answer.variable,
            domain=answer.domain,
            strict_domain=False,
        )
        try:
            outcome = pool.submit(CheckRequest(spec, submitted)).outcome
        except Exception:  # busy, closed or any surprise: no match
            return None
        if isinstance(outcome, Verdict) and outcome.status is VerdictStatus.CORRECT:
            return misconception_note(entry)
    return None


def build_context(
    db: Session, item: SessionItem, problem: Problem, hint_level: int, pool: Pool
) -> HelpContext:
    """Read the item's applied results (a stored-but-not-applied result changed nothing for the
    student), then assemble. The pool is called here, so the caller holds no write
    transaction. ``tries_used`` is the item's own counter."""
    rows = db.execute(
        select(Submission, AttemptResult)
        .join(AttemptResult, AttemptResult.submission_pk == Submission.id)
        .where(Submission.session_item_id == item.id, AttemptResult.applied.is_(True))
        .order_by(Submission.id)
    ).all()
    choices = (
        {c.id: c.latex for c in problem.answer.choices}
        if isinstance(problem.answer, ChoiceAnswer)
        else {}
    )
    attempts: list[AttemptLine] = []
    last_choice: str | None = None
    for sub, result in rows:
        picked = loads_exact(sub.answer_json).get("choice_id")
        last_choice = picked if isinstance(picked, str) else None
        latex = choices.get(last_choice or "", "") if choices else (sub.answer_latex or "")
        attempts.append(AttemptLine(latex, result.status))
    latest = attempts[-1] if attempts else None
    note = match_misconception(problem, latest, last_choice, pool)
    context = assemble_context(problem, attempts, hint_level, note)
    return replace(context, tries_used=item.tries_used)


def load_confusions(path: Path) -> dict[str, list[Confusion]]:
    """Per-topic "I'm confused about..." entries; ValueError on any malformed entry."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a mapping of topic to entries")
    out: dict[str, list[Confusion]] = {}
    for topic, entries in data.items():
        if not isinstance(entries, list):
            raise ValueError(f"{path.name}: {topic}: expected a list")
        seen: set[str] = set()
        parsed: list[Confusion] = []
        for entry in entries:
            fields = entry if isinstance(entry, dict) else {}
            cid, label = fields.get("id"), fields.get("label")
            if not isinstance(cid, str) or not _CONFUSION_ID.match(cid) or cid in seen:
                raise ValueError(f"{path.name}: {topic}: bad or duplicate id {cid!r}")
            if not isinstance(label, str) or not 0 < len(label) <= MAX_LABEL:
                raise ValueError(f"{path.name}: {topic}: {cid}: label must be 1-{MAX_LABEL} chars")
            seen.add(cid)
            parsed.append(Confusion(cid, label))
        out[str(topic)] = parsed
    return out
