"""PracticeService against a real SQLite file and a scripted fake pool."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from mathtutor.application.auth import AuthService
from mathtutor.application.errors import (
    Busy,
    Forbidden,
    InvalidAction,
    InvalidInput,
    NotFound,
    StaleItem,
    SubmissionPending,
)
from mathtutor.application.practice import Done, ItemView, PracticeService, SubmitView
from mathtutor.content.loader import load_bundle
from mathtutor.domain import (
    Action,
    AnswerKind,
    FormatIssueCode,
    ItemState,
    Method,
    VerdictReason,
    VerdictStatus,
)
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade
from mathtutor.store.models import AttemptResult, ItemEvent, SessionItem, StudySession, Submission
from mathtutor.verify.types import (
    CheckRequest,
    CheckResult,
    FormatIssue,
    SubmittedAnswer,
    Verdict,
    VerifierBusy,
)

ROOT = Path(__file__).resolve().parents[3]
CONTENT = load_bundle(ROOT / "content" / "compiled" / "problems.json")
BASIC = "derivatives.basic_rules"
FIRST, SECOND = "openstax-c1-3.3-115", "openstax-c1-3.3-111"

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
INCORRECT = Verdict(VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION)
UNABLE = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.NOT_PROVEN, Method.NONE)
ANSWER = SubmittedAnswer(AnswerKind.EXPRESSION, ["Multiply", 2, "x"], "2x", None)

Outcome = Verdict | FormatIssue | type[VerifierBusy]


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class FakePool:
    """Returns scripted outcomes in order; ``during`` runs while 'grading'."""

    def __init__(self) -> None:
        self.script: list[Outcome] = []
        self.requests: list[CheckRequest] = []
        self.during: Callable[[], None] | None = None

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        if self.during is not None:
            hook, self.during = self.during, None
            hook()
        outcome = self.script.pop(0)
        if outcome is VerifierBusy:
            raise VerifierBusy("full")
        assert isinstance(outcome, Verdict | FormatIssue)
        return CheckResult(outcome, "0.1.0+test", worker_ms=7, queue_ms=1)


class World:
    def __init__(self, tmp_path: Path) -> None:
        url = f"sqlite:///{(tmp_path / 'practice.db').as_posix()}"
        upgrade(url)
        self.engine = make_engine(url)
        self.sessions = make_sessionmaker(self.engine)
        self.clock = Clock()
        self.pool = FakePool()
        self.svc = PracticeService(self.sessions, CONTENT, self.pool, self.clock)
        auth = AuthService(self.sessions, self.clock)
        self.alice = auth.register("alice", "password-1").user_id
        self.bob = auth.register("bob", "password-2").user_id

    def view(self, session_id: int, user: int | None = None) -> ItemView:
        v = self.svc.current_item(self.alice if user is None else user, session_id)
        assert isinstance(v, ItemView)
        return v

    def submit(
        self, session_id: int, outcome: Outcome, *, sid: uuid.UUID | None = None, **kw: object
    ) -> SubmitView:
        v = self.view(session_id)
        self.pool.script.append(outcome)
        args: dict[str, object] = {
            "user_id": self.alice,
            "session_id": session_id,
            "submission_id": sid or uuid.uuid4(),
            "session_item_id": v.session_item_id,
            "item_revision": v.revision,
            "answer": ANSWER,
        }
        args.update(kw)
        return self.svc.submit_answer(**args)  # type: ignore[arg-type]

    def count(self, model: type) -> int:
        with self.sessions() as db:
            return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _at(view: ItemView) -> tuple[int, int]:
    """An action's target: the presentation and its revision."""
    return view.session_item_id, view.revision


@pytest.fixture
def w(tmp_path: Path) -> Iterator[World]:
    world = World(tmp_path)
    yield world
    world.engine.dispose()


def test_start_creates_first_presentation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    assert v.item_id == FIRST
    assert v.state is ItemState.ACTIVE
    assert v.tries_left == 3
    assert v.allowed_actions == [Action.SUBMIT, Action.SKIP]
    assert v.precision_hint is None  # only numeric problems get a hint
    assert v.last_outcome is None and v.revealed_latex is None
    assert v.statement_html


def test_unknown_topic_is_invalid(w: World) -> None:
    with pytest.raises(InvalidAction):
        w.svc.start_session(w.alice, ["derivatives.nope"])
    with pytest.raises(InvalidAction):
        w.svc.start_session(w.alice, [])


def test_precision_hint_and_choices(w: World) -> None:
    sid = w.svc.start_session(w.alice, ["derivatives.chain_rule"])
    for _ in range(3):
        w.submit(sid, INCORRECT)
    w.svc.advance(w.alice, sid, *_at(w.view(sid)))
    v = w.view(sid)
    assert v.item_id == "openstax-c1-3.6-253"
    assert v.precision_hint == "Round to 3 decimal places"
    trig = w.svc.start_session(w.alice, ["derivatives.trig"])
    choice = w.view(trig)
    assert choice.answer_kind is AnswerKind.CHOICE
    assert choice.precision_hint is None
    assert choice.choices is not None and [c[0] for c in choice.choices][:2] == ["a", "b"]


def test_three_incorrect_exhausts(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    lefts, states = [], []
    for _ in range(3):
        r = w.submit(sid, INCORRECT)
        assert r.outcome == INCORRECT and not r.replayed
        lefts.append(r.item.tries_left)
        states.append(r.item.state)
    assert lefts == [2, 1, 0]
    assert states == [ItemState.ACTIVE, ItemState.ACTIVE, ItemState.EXHAUSTED]
    assert w.view(sid).allowed_actions == [Action.REVEAL, Action.ADVANCE]
    assert w.view(sid).last_outcome == INCORRECT


def test_unable_to_verify_keeps_try_and_allows_skip(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    r = w.submit(sid, UNABLE)
    assert r.item.tries_left == 3
    assert r.item.state is ItemState.ACTIVE
    assert Action.SKIP in r.item.allowed_actions
    nxt = w.svc.skip(w.alice, sid, *_at(r.item))
    assert isinstance(nxt, ItemView) and nxt.item_id == SECOND
    with w.sessions() as db:
        assert db.scalar(select(ItemEvent.kind)) is Action.SKIP


def test_correct_then_advance_creates_new_presentation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    first = w.view(sid)
    r = w.submit(sid, CORRECT)
    assert r.item.state is ItemState.ANSWERED
    assert r.item.allowed_actions == [Action.ADVANCE]
    assert r.item.revision == first.revision + 1
    with pytest.raises(InvalidAction):
        w.svc.skip(w.alice, sid, *_at(r.item))
    nxt = w.svc.advance(w.alice, sid, *_at(r.item))
    assert isinstance(nxt, ItemView)
    assert nxt.item_id == SECOND and nxt.session_item_id != first.session_item_id
    with w.sessions() as db:
        old = db.get(SessionItem, first.session_item_id)
        assert old is not None and old.state is ItemState.COMPLETED
        assert old.completed_at == w.clock.now


def test_reveal_only_when_exhausted(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    with pytest.raises(InvalidAction):
        w.svc.reveal(w.alice, sid, *_at(w.view(sid)))
    for _ in range(3):
        w.submit(sid, INCORRECT)
    v = w.svc.reveal(w.alice, sid, *_at(w.view(sid)))
    assert isinstance(v, ItemView)
    assert v.state is ItemState.REVEALED
    assert v.revealed_latex
    assert v.allowed_actions == [Action.ADVANCE]
    assert w.view(sid).revealed_latex == v.revealed_latex


def test_revisit_gets_fresh_presentation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    first = w.view(sid)
    w.svc.skip(w.alice, sid, *_at(first))
    w.submit(sid, CORRECT)  # SECOND
    again = w.svc.advance(w.alice, sid, *_at(w.view(sid)))
    assert isinstance(again, ItemView)
    assert again.item_id == FIRST
    assert again.session_item_id != first.session_item_id
    assert again.tries_left == 3 and again.last_outcome is None


def test_duplicate_submission_id_returns_stored_result(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    key = uuid.uuid4()
    first = w.submit(sid, INCORRECT, sid=key)
    again = w.svc.submit_answer(w.alice, sid, key, v.session_item_id, v.revision, ANSWER)
    assert again.replayed and again.outcome == INCORRECT
    assert again.item.tries_left == first.item.tries_left == 2
    assert w.count(AttemptResult) == 1
    assert len(w.pool.requests) == 1


def test_stale_revision_is_409(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    w.submit(sid, INCORRECT)
    with pytest.raises(StaleItem):
        w.svc.submit_answer(w.alice, sid, uuid.uuid4(), v.session_item_id, v.revision, ANSWER)
    with pytest.raises(StaleItem):
        w.svc.skip(w.alice, sid, *_at(v))


def test_revision_changed_while_grading_stores_unapplied_result(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    w.pool.during = lambda: w.svc.skip(w.alice, sid, *_at(v))
    key = uuid.uuid4()
    with pytest.raises(StaleItem):
        w.submit(sid, CORRECT, sid=key)
    with w.sessions() as db:
        result = db.scalar(select(AttemptResult))
        assert result is not None
        assert (result.applied, result.counts_as_try) == (False, False)
    # The replay reports the same conflict.
    with pytest.raises(StaleItem):
        w.svc.submit_answer(w.alice, sid, key, v.session_item_id, v.revision, ANSWER)


def test_other_users_session_forbidden(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    bob = w.bob
    with pytest.raises(Forbidden):
        w.svc.current_item(bob, sid)
    with pytest.raises(Forbidden):
        w.svc.submit_answer(bob, sid, uuid.uuid4(), v.session_item_id, v.revision, ANSWER)
    for action in (w.svc.advance, w.svc.skip, w.svc.reveal):
        with pytest.raises(Forbidden):
            action(bob, sid, *_at(v))
    with pytest.raises(NotFound):
        w.svc.current_item(w.alice, sid + 100)
    # A replayed submission id is only visible to its owner.
    key = uuid.uuid4()
    w.submit(sid, INCORRECT, sid=key)
    bob_sid = w.svc.start_session(bob, [BASIC])
    bv = w.view(bob_sid, user=bob)
    with pytest.raises(Forbidden):
        w.svc.submit_answer(bob, bob_sid, key, bv.session_item_id, bv.revision, ANSWER)
    assert w.count(Submission) == 1


def test_item_from_another_session_is_not_found(w: World) -> None:
    s1 = w.svc.start_session(w.alice, [BASIC])
    s2 = w.svc.start_session(w.alice, [BASIC])
    v1 = w.view(s1)
    with pytest.raises(NotFound):
        w.svc.submit_answer(w.alice, s2, uuid.uuid4(), v1.session_item_id, v1.revision, ANSWER)


def test_answer_kind_must_match(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    choice = SubmittedAnswer(AnswerKind.CHOICE, None, "", "a")
    with pytest.raises(InvalidInput):
        w.submit(sid, CORRECT, answer=choice)
    assert w.count(Submission) == 0


def test_busy_releases_reservation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    before = w.view(sid)
    with pytest.raises(Busy):
        w.submit(sid, VerifierBusy)
    assert w.count(Submission) == 0
    after = w.view(sid)
    assert (after.revision, after.tries_left) == (before.revision, before.tries_left)


def test_format_issue_changes_nothing(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    before = w.view(sid)
    issue = FormatIssue(FormatIssueCode.INCOMPLETE, "")
    r = w.submit(sid, issue)
    assert r.outcome == issue
    assert w.count(Submission) == 0 and w.count(AttemptResult) == 0
    after = w.view(sid)
    assert (after.revision, after.tries_left, after.state) == (
        before.revision,
        before.tries_left,
        before.state,
    )


def test_current_is_read_only(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    a = w.view(sid)
    w.clock.now += timedelta(minutes=5)
    b = w.view(sid)
    assert a == b
    with w.sessions() as db:
        item = db.get(SessionItem, a.session_item_id)
        assert item is not None and item.served_at == datetime(2026, 10, 21, 12, 0, tzinfo=UTC)


def test_seconds_on_item_from_served_at(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    w.clock.now += timedelta(seconds=42, milliseconds=600)
    w.view(sid)  # refresh: no effect
    w.submit(sid, INCORRECT)
    with w.sessions() as db:
        result = db.scalar(select(AttemptResult))
        assert result is not None
        assert result.seconds_on_item == 42
        assert (result.worker_ms, result.queue_ms) == (7, 1)
        assert result.verifier_version == "0.1.0+test"
        assert result.counts_as_try and result.applied


def test_pending_reservation_then_replay_regrades_orphaned_reservation(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    key = uuid.uuid4()
    # Simulate a crash between transactions A and B: a reservation with no result.
    with w.sessions.begin() as db:
        db.add(
            Submission(
                submission_id=str(key),
                session_item_id=v.session_item_id,
                answer_kind=AnswerKind.EXPRESSION,
                answer_json='{"mathjson": ["Multiply", 2, "x"], "choice_id": null}',
                answer_latex="2x",
                created_at=w.clock.now,
            )
        )
    w.clock.now += timedelta(seconds=9)
    with pytest.raises(SubmissionPending):
        w.svc.submit_answer(w.alice, sid, key, v.session_item_id, v.revision, ANSWER)
    w.clock.now += timedelta(seconds=1)
    w.pool.script.append(CORRECT)
    r = w.svc.submit_answer(w.alice, sid, key, v.session_item_id, v.revision, ANSWER)
    assert r.outcome == CORRECT and r.item.state is ItemState.ANSWERED
    assert w.pool.requests[-1].answer == ANSWER
    assert w.count(Submission) == 1 and w.count(AttemptResult) == 1


def test_decimal_answer_round_trips_exactly(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    v = w.view(sid)
    key = uuid.uuid4()
    exact = SubmittedAnswer(AnswerKind.EXPRESSION, ["Multiply", {"num": "0.1"}, "x"], "0.1x", None)
    with w.sessions.begin() as db:
        db.add(
            Submission(
                submission_id=str(key),
                session_item_id=v.session_item_id,
                answer_kind=AnswerKind.EXPRESSION,
                answer_json='{"mathjson": ["Multiply", 0.1, "x"], "choice_id": null}',
                answer_latex="0.1x",
                created_at=w.clock.now - timedelta(seconds=30),
            )
        )
    w.pool.script.append(INCORRECT)
    w.svc.submit_answer(w.alice, sid, key, v.session_item_id, v.revision, exact)
    assert w.pool.requests[-1].answer == exact


def test_done_when_all_answered(w: World) -> None:
    sid = w.svc.start_session(w.alice, [BASIC])
    w.submit(sid, CORRECT)
    w.svc.advance(w.alice, sid, *_at(w.view(sid)))
    w.submit(sid, CORRECT)
    done = w.svc.advance(w.alice, sid, *_at(w.view(sid)))
    assert done == Done("all_correct")
    assert w.svc.current_item(w.alice, sid) == Done("all_correct")
    with w.sessions() as db:
        session = db.get(StudySession, sid)
        assert session is not None and session.ended_at == w.clock.now
    # Starting again on mastered topics gives a finished session.
    again = w.svc.start_session(w.alice, [BASIC])
    assert w.svc.current_item(w.alice, again) == Done("all_correct")


def test_session_summary(w: World) -> None:
    s1 = w.svc.start_session(w.alice, [BASIC])
    w.submit(s1, INCORRECT)
    w.submit(s1, CORRECT)
    w.svc.advance(w.alice, s1, *_at(w.view(s1)))
    w.submit(s1, UNABLE)
    w.clock.now += timedelta(minutes=1)
    s2 = w.svc.start_session(w.alice, ["derivatives.trig"])
    summaries = w.svc.session_summary(w.alice)
    assert [s.session_id for s in summaries] == [s2, s1]
    assert (summaries[1].answered, summaries[1].correct) == (2, 1)
    assert summaries[1].topics == [BASIC]
    assert w.svc.session_summary(w.bob) == []
