"""Server-owned help context, misconception matching and confusion lists (Task 9)."""

from __future__ import annotations

import dataclasses
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import ChoiceAnswer, Problem
from mathtutor.domain import AnswerKind, ItemState, Method, VerdictReason, VerdictStatus
from mathtutor.help.context import (
    AttemptLine,
    HelpContext,
    assemble_context,
    build_context,
    load_confusions,
    match_misconception,
    misconception_note,
)
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade, write_transaction
from mathtutor.store.models import (
    AttemptResult,
    SessionItem,
    StudySession,
    Submission,
    User,
)
from mathtutor.verify.types import CheckRequest, CheckResult, Verdict, VerifierBusy

ROOT = Path(__file__).parents[3]
BUNDLE = load_bundle(ROOT / "content" / "compiled" / "problems.json")
PROBLEMS = {p.id: p for p in BUNDLE.bundle.problems}
CONFUSIONS = ROOT / "content" / "help" / "confusions.yaml"
CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
WRONG = Verdict(VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION)
INC = AttemptLine("x", VerdictStatus.INCORRECT)


class ScriptedPool:
    """Returns ``verdicts`` in order (a ``VerifierBusy`` is raised); records requests."""

    def __init__(self, *verdicts: Verdict | type[VerifierBusy]) -> None:
        self.verdicts = list(verdicts)
        self.requests: list[CheckRequest] = []

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        v = self.verdicts.pop(0) if self.verdicts else WRONG
        if v is VerifierBusy:
            raise VerifierBusy("busy")
        assert isinstance(v, Verdict)
        return CheckResult(v, "t")


def _answer_strings(p: Problem) -> list[str]:
    a = p.answer
    if isinstance(a, ChoiceAnswer):
        return [c.latex for c in a.choices if c.id == a.correct]
    return [a.latex]


def _dump(ctx: HelpContext) -> str:
    return json.dumps(dataclasses.asdict(ctx), default=str)


def test_context_excludes_answer() -> None:
    for p in BUNDLE.bundle.problems:
        for note in (None, *(misconception_note(m) for m in p.misconceptions)):
            text = _dump(assemble_context(p, [], 1, note))
            for secret in _answer_strings(p):
                assert secret not in text, p.id
            if isinstance(p.answer, ChoiceAnswer):
                assert '"correct"' not in text
            if p.review.notes:
                assert p.review.notes not in text
            assert "review" not in text


def test_attempts_newest_first_capped() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    attempts = [AttemptLine(f"a{i}", VerdictStatus.INCORRECT) for i in range(5)]
    attempts.append(AttemptLine("z" * 500, VerdictStatus.UNABLE_TO_VERIFY))
    ctx = assemble_context(p, attempts, 2, None)
    assert [a.latex[:2] for a in ctx.attempts] == ["zz", "a4", "a3"]
    assert len(ctx.attempts[0].latex.encode()) <= 400
    assert ctx.attempts[0].status is VerdictStatus.UNABLE_TO_VERIFY
    assert (ctx.hint_level, ctx.topic, ctx.section) == (2, p.topic, "3.6")
    assert ctx.problem_id == p.id and ctx.variable == "x"


def test_unable_attempt_is_never_matched() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    pool = ScriptedPool(CORRECT)
    latest = AttemptLine("18(7x-4)^2", VerdictStatus.UNABLE_TO_VERIFY)
    assert match_misconception(p, latest, None, pool) is None
    assert pool.requests == []


def test_misconception_expression_match() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    pool = ScriptedPool(CORRECT)
    latest = AttemptLine("18(7x-4)^2", VerdictStatus.INCORRECT)
    assert match_misconception(p, latest, None, pool) == "missing du/dx = 7"
    assert len(pool.requests) == 1
    spec = pool.requests[0].answer_spec
    assert spec.kind == "expression" and spec.latex == "18(7x-4)^2"  # type: ignore[union-attr]


def test_second_misconception_matches_after_first_misses() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    pool = ScriptedPool(WRONG, CORRECT)
    out = match_misconception(p, AttemptLine("42(7x-4)^2", VerdictStatus.INCORRECT), None, pool)
    assert out == "forgot the factor 3 from the power rule"


def test_misconception_choice_match() -> None:
    p = PROBLEMS["adapted-c1-3.5-x2cosx"]
    pool = ScriptedPool()
    latest = AttemptLine("2x\\cos(x)+x^2\\sin(x)", VerdictStatus.INCORRECT)
    note = match_misconception(p, latest, "b", pool)
    assert note == "sign error: derivative of cos x taken as +sin x"
    assert pool.requests == []
    assert match_misconception(p, latest, "a", pool) is None


def test_no_match_no_note() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    pool = ScriptedPool()
    latest = AttemptLine("5x", VerdictStatus.INCORRECT)
    assert match_misconception(p, latest, None, pool) is None
    assert assemble_context(p, [latest], 1, None).misconception_note is None
    assert match_misconception(p, None, None, pool) is None


def test_busy_pool_is_no_match() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    pool = ScriptedPool(VerifierBusy)
    latest = AttemptLine("18(7x-4)^2", VerdictStatus.INCORRECT)
    assert match_misconception(p, latest, None, pool) is None


def test_deadline_stops_matching() -> None:
    p = PROBLEMS["openstax-c1-3.6-215"]
    ticks = iter([0.0, 5.0, 5.0, 5.0])
    pool = ScriptedPool(CORRECT)
    latest = AttemptLine("18(7x-4)^2", VerdictStatus.INCORRECT)
    out = match_misconception(p, latest, None, pool, clock=lambda: next(ticks))
    assert out is None and pool.requests == []


def test_misconception_note_text() -> None:
    assert misconception_note("18x  # missing factor") == "missing factor"
    assert misconception_note("18x") is None
    assert misconception_note("18x  #   ") is None


def test_content_check_requires_notes() -> None:
    from mathtutor.verify import content_check

    assert content_check.check_bundle(BUNDLE) == []
    first = BUNDLE.bundle.problems[0]
    assert first.misconceptions
    bad = first.model_copy(update={"misconceptions": ["3x^2"] * len(first.misconceptions)})
    problems = [bad, *BUNDLE.bundle.problems[1:]]
    content = dataclasses.replace(
        BUNDLE, bundle=BUNDLE.bundle.model_copy(update={"problems": problems})
    )
    errors = content_check.check_bundle(content)
    assert any("misconceptions[0]: needs a note" in e for e in errors)


def test_confusions_valid() -> None:
    data = load_confusions(CONFUSIONS)
    topics = {t.topic_id for t in BUNDLE.bundle.topics}
    assert set(data) == topics
    for topic, entries in data.items():
        assert 3 <= len(entries) <= 5, topic
        ids = [e.id for e in entries]
        assert len(set(ids)) == len(ids)
        for e in entries:
            assert re.fullmatch(r"[a-z_]{3,40}", e.id)
            assert 0 < len(e.label) <= 80
            assert not re.search(r"\b(color|behavior|center|analyze)\b", e.label)


def test_confusions_rejects_bad_file(tmp_path: Path) -> None:
    path = tmp_path / "c.yaml"
    path.write_text("t:\n  - {id: Bad-Id, label: x}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_confusions(path)


def test_build_context_reads_submissions(tmp_path: Path) -> None:
    url = f"sqlite:///{(tmp_path / 'c.db').as_posix()}"
    upgrade(url)
    engine = make_engine(url)
    sessions: sessionmaker[Session] = make_sessionmaker(engine)
    p = PROBLEMS["openstax-c1-3.6-215"]
    now = datetime(2026, 10, 26, tzinfo=UTC)
    with write_transaction(sessions) as db:
        user = User(username="ctx_user", password_hash="x", created_at=now)
        sess = StudySession(user=user, mode="practice", topics=[], started_at=now)
        item = SessionItem(
            session=sess,
            item_id=p.id,
            content_version="v",
            problem_json="{}",
            sequence=1,
            state=ItemState.ACTIVE,
            revision=0,
            served_at=now,
            tries_used=2,
        )
        db.add_all([user, sess, item])
        db.flush()
        for n, (latex, status) in enumerate(
            [("5x", VerdictStatus.INCORRECT), ("18(7x-4)^2", VerdictStatus.INCORRECT)]
        ):
            sub = Submission(
                submission_id=f"s{n}",
                session_item_id=item.id,
                answer_kind=AnswerKind.EXPRESSION,
                answer_json=json.dumps({"mathjson": None, "choice_id": None}),
                answer_latex=latex,
                created_at=now,
            )
            db.add(sub)
            db.flush()
            db.add(
                AttemptResult(
                    submission_pk=sub.id,
                    status=status,
                    reason=VerdictReason.COUNTEREXAMPLE,
                    method=Method.REFUTATION,
                    verifier_version="t",
                    worker_ms=0,
                    queue_ms=0,
                    seconds_on_item=1,
                    counts_as_try=True,
                    applied=True,
                )
            )
        item_id = item.id
    with sessions() as db:
        item = db.get(SessionItem, item_id)
        assert item is not None
        ctx = build_context(db, item, p, 3, ScriptedPool(CORRECT))
    assert [a.latex for a in ctx.attempts] == ["18(7x-4)^2", "5x"]
    assert ctx.tries_used == 2 and ctx.hint_level == 3
    assert ctx.misconception_note == "missing du/dx = 7"
    engine.dispose()
