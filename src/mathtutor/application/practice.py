"""Practice sessions: presentations, the submit protocol and actions (spec 06).

Every transaction is short; the verifier pool is only ever called with no transaction open.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import (
    Busy,
    DatabaseBusy,
    Forbidden,
    InvalidAction,
    InvalidInput,
    NotFound,
    StaleItem,
    SubmissionPending,
)
from mathtutor.application.selection import History, next_item_id
from mathtutor.content.loader import LoadedContent
from mathtutor.content.schema import Answer, ChoiceAnswer, Decimals, NumericAnswer, Problem, Source
from mathtutor.domain import Action, AnswerKind, ItemState, VerdictStatus
from mathtutor.jsonio import loads_exact
from mathtutor.store.db import is_lock_error, write_transaction
from mathtutor.store.models import AttemptResult, ItemEvent, SessionItem, StudySession, Submission
from mathtutor.verify.types import (
    CheckRequest,
    CheckResult,
    FormatIssue,
    SubmittedAnswer,
    Verdict,
    VerifierBusy,
)

MAX_TRIES = 3
ORPHAN_AFTER = timedelta(seconds=10)  # ruling R5 / R13
ALL_CORRECT = "all_correct"  # every problem in the topics has been answered correctly
SESSION_COMPLETE = "session_complete"  # every unsolved problem was shown in this session

ALLOWED: dict[ItemState, list[Action]] = {
    ItemState.ACTIVE: [Action.SUBMIT, Action.SKIP],
    ItemState.ANSWERED: [Action.ADVANCE],
    ItemState.EXHAUSTED: [Action.REVEAL, Action.ADVANCE],
    ItemState.REVEALED: [Action.ADVANCE],
    ItemState.COMPLETED: [],
}


class Pool(Protocol):
    def submit(self, req: CheckRequest) -> CheckResult: ...


@dataclass(frozen=True)
class Done:
    reason: str


@dataclass(frozen=True)
class ItemView:
    session_item_id: int
    revision: int
    state: ItemState
    item_id: str
    statement_html: str
    answer_kind: AnswerKind
    precision_hint: str | None
    choices: list[tuple[str, str]] | None
    source: Source
    allowed_actions: list[Action]
    tries_left: int
    last_outcome: Verdict | FormatIssue | None
    revealed_latex: str | None


@dataclass(frozen=True)
class SubmitView:
    outcome: Verdict | FormatIssue
    item: ItemView
    replayed: bool
    worker_ms: int | None = None  # for request logs; None on a replay
    queue_ms: int | None = None


@dataclass(frozen=True)
class SessionSummary:
    session_id: int
    topics: list[str]
    started_at: datetime
    answered: int
    correct: int


@dataclass(frozen=True)
class _Reservation:
    submission_pk: int
    submission_id: str
    session_item_id: int
    expected_revision: int
    answer_spec: Answer
    answer: SubmittedAnswer


def precision_hint(answer: Answer) -> str | None:
    if not isinstance(answer, NumericAnswer):
        return None
    if isinstance(answer.precision, Decimals):
        n = answer.precision.decimals
        return f"Round to {n} decimal place{'' if n == 1 else 's'}"
    return "Give an exact answer"


def expected_latex(answer: Answer) -> str:
    if isinstance(answer, ChoiceAnswer):
        return next(c.latex for c in answer.choices if c.id == answer.correct)
    return answer.latex


def _transition(state: ItemState, tries: int, status: VerdictStatus) -> tuple[ItemState, int]:
    if status is VerdictStatus.CORRECT:
        return ItemState.ANSWERED, tries
    if status is VerdictStatus.INCORRECT:
        tries += 1
        return (ItemState.EXHAUSTED if tries >= MAX_TRIES else ItemState.ACTIVE), tries
    return state, tries  # unable_to_verify: no try consumed


def _encode_answer(answer: SubmittedAnswer) -> str:
    return json.dumps({"mathjson": answer.mathjson, "choice_id": answer.choice_id})


def _decode_answer(sub: Submission) -> SubmittedAnswer:
    data = loads_exact(sub.answer_json)
    return SubmittedAnswer(
        sub.answer_kind, data["mathjson"], sub.answer_latex or "", data["choice_id"]
    )


class PracticeService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        content: LoadedContent,
        pool: Pool,
        clock: Callable[[], datetime],
    ) -> None:
        self._sessions = sessions
        self._content = content
        self._pool = pool
        self._clock = clock
        self._problems: dict[str, Problem] = {p.id: p for p in content.bundle.problems}
        self._snapshots: dict[tuple[str, str], Problem] = {}
        self._topics = {t.topic_id for t in content.bundle.topics}

    # -- sessions ---------------------------------------------------------------------------

    def start_session(self, user_id: int, topics: list[str]) -> int:
        chosen = list(dict.fromkeys(topics))
        unknown = [t for t in chosen if t not in self._topics]
        if not chosen or unknown:
            raise InvalidAction("Choose at least one known topic.", code="unknown_topic")
        with self._tx() as db:
            reusable = self._untouched_session(db, user_id, chosen)
            if reusable is not None:
                return reusable  # pressing "Start" again must not pile up empty sessions
            session = StudySession(
                user_id=user_id, mode="practice", topics=chosen, started_at=self._clock()
            )
            db.add(session)
            db.flush()
            self._present_next(db, session, sequence=1)
            return session.id

    def current_item(self, user_id: int, session_id: int) -> ItemView | Done:
        """Read-only: never inserts or updates a row."""
        with self._sessions() as db:
            session = self._owned(db, user_id, session_id)
            item = self._current(db, session)
            if session.ended_at is not None or item is None or item.state is ItemState.COMPLETED:
                return Done(self._done_reason(db, session))
            return self._view(db, item)

    def _untouched_session(self, db: Session, user_id: int, topics: list[str]) -> int | None:
        """The user's latest open session on the same topics, if nothing was submitted or
        skipped in it yet."""
        latest = db.scalar(
            select(StudySession)
            .where(StudySession.user_id == user_id, StudySession.ended_at.is_(None))
            .order_by(StudySession.id.desc())
            .limit(1)
        )
        if latest is None or sorted(latest.topics) != sorted(topics):
            return None
        item_ids = select(SessionItem.id).where(SessionItem.session_id == latest.id)
        touched = db.scalar(
            select(Submission.id).where(Submission.session_item_id.in_(item_ids)).limit(1)
        ) or db.scalar(select(ItemEvent.id).where(ItemEvent.session_item_id.in_(item_ids)).limit(1))
        return None if touched else latest.id

    def session_summary(self, user_id: int) -> list[SessionSummary]:
        with self._sessions() as db:
            sessions = db.scalars(
                select(StudySession)
                .where(StudySession.user_id == user_id)
                .order_by(StudySession.started_at.desc(), StudySession.id.desc())
            ).all()
            rows = db.execute(
                select(SessionItem.session_id, SessionItem.id, AttemptResult.status)
                .join(Submission, Submission.session_item_id == SessionItem.id)
                .join(AttemptResult, AttemptResult.submission_pk == Submission.id)
                .join(StudySession, StudySession.id == SessionItem.session_id)
                .where(StudySession.user_id == user_id, AttemptResult.applied.is_(True))
            ).all()
        answered: dict[int, set[int]] = {}
        correct: dict[int, set[int]] = {}
        for session_id, item_id, status in rows:
            answered.setdefault(session_id, set()).add(item_id)
            if status is VerdictStatus.CORRECT:
                correct.setdefault(session_id, set()).add(item_id)
        return [
            SessionSummary(
                session_id=s.id,
                topics=list(s.topics),
                started_at=s.started_at,
                answered=len(answered.get(s.id, ())),
                correct=len(correct.get(s.id, ())),
            )
            for s in sessions
            if s.id in answered  # a session nothing was answered in is not history
        ]

    # -- actions ----------------------------------------------------------------------------

    def advance(
        self, user_id: int, session_id: int, session_item_id: int, item_revision: int
    ) -> ItemView | Done:
        return self._act(user_id, session_id, session_item_id, item_revision, Action.ADVANCE)

    def skip(
        self, user_id: int, session_id: int, session_item_id: int, item_revision: int
    ) -> ItemView | Done:
        return self._act(user_id, session_id, session_item_id, item_revision, Action.SKIP)

    def reveal(
        self, user_id: int, session_id: int, session_item_id: int, item_revision: int
    ) -> ItemView | Done:
        return self._act(user_id, session_id, session_item_id, item_revision, Action.REVEAL)

    def _act(
        self,
        user_id: int,
        session_id: int,
        session_item_id: int,
        item_revision: int,
        action: Action,
    ) -> ItemView | Done:
        """Every action names its presentation: revisions restart at 0 on each new one, so a
        revision alone could let a repeated Skip land on the next problem (review B-A1)."""
        with self._tx() as db:
            session = self._owned(db, user_id, session_id)
            item = self._current(db, session)
            if session.ended_at is not None or item is None:
                raise InvalidAction("This session is finished.", code="session_finished")
            if item.id != session_item_id or item.revision != item_revision:
                raise StaleItem("This problem changed; reload it.")
            if action not in ALLOWED[item.state]:
                raise InvalidAction(f"You can't {action.value} this problem now.")
            now = self._clock()
            db.add(ItemEvent(session_item_id=item.id, kind=action, created_at=now))
            item.revision += 1
            if action is Action.REVEAL:
                item.state = ItemState.REVEALED
                db.flush()
                return self._view(db, item)
            item.state = ItemState.COMPLETED
            item.completed_at = now
            db.flush()
            nxt = self._present_next(db, session, sequence=item.sequence + 1)
            return Done(self._done_reason(db, session)) if nxt is None else self._view(db, nxt)

    # -- submit (spec 06 "Submission protocol") ---------------------------------------------

    def submit_answer(
        self,
        user_id: int,
        session_id: int,
        submission_id: UUID,
        session_item_id: int,
        item_revision: int,
        answer: SubmittedAnswer,
    ) -> SubmitView:
        key = str(submission_id)
        # 1. Replay check.
        replay = self._replay(user_id, session_id, key, item_revision)
        if isinstance(replay, SubmitView):
            return replay
        if replay is None:
            # 2. Transaction A: reserve the submission id.
            try:
                reservation = self._reserve(
                    user_id, session_id, key, session_item_id, item_revision, answer
                )
            except IntegrityError:
                # A concurrent request with the same id reserved first.
                replay = self._replay(user_id, session_id, key, item_revision)
                if isinstance(replay, SubmitView):
                    return replay
                if replay is None:
                    raise StaleItem("This problem changed; reload it.") from None
                reservation = replay
        else:
            reservation = replay  # R5: an orphaned reservation is graded again.
        return self._grade(user_id, session_id, reservation)

    def _replay(
        self, user_id: int, session_id: int, key: str, item_revision: int
    ) -> SubmitView | _Reservation | None:
        with self._sessions() as db:
            sub = db.scalar(select(Submission).where(Submission.submission_id == key))
            if sub is None:
                return None
            item = sub.session_item
            if item.session.user_id != user_id:
                raise Forbidden("This is not your submission.")
            if item.session_id != session_id:
                raise NotFound("Submission not found in this session.")
            result = sub.result
            if result is not None:
                if not result.applied:
                    raise StaleItem("This problem changed while it was being checked.")
                verdict = Verdict(result.status, result.reason, result.method)
                return SubmitView(verdict, self._view(db, item), replayed=True)
            if self._clock() - sub.created_at < ORPHAN_AFTER:
                raise SubmissionPending("This answer is still being checked.")
            return _Reservation(
                submission_pk=sub.id,
                submission_id=key,
                session_item_id=item.id,
                expected_revision=item_revision,
                answer_spec=self._snapshot(item).answer,
                answer=_decode_answer(sub),
            )

    def _reserve(
        self,
        user_id: int,
        session_id: int,
        key: str,
        session_item_id: int,
        item_revision: int,
        answer: SubmittedAnswer,
    ) -> _Reservation:
        with self._tx() as db:
            session = self._owned(db, user_id, session_id)
            item = db.get(SessionItem, session_item_id)
            if item is None or item.session_id != session.id:
                raise NotFound("Problem not found in this session.")
            spec = self._snapshot(item).answer
            if answer.kind.value != spec.kind:
                raise InvalidInput(
                    f"This problem expects a {spec.kind} answer.", code="kind_mismatch"
                )
            if item.state is not ItemState.ACTIVE or item.revision != item_revision:
                raise StaleItem("This problem changed; reload it.")
            sub = Submission(
                submission_id=key,
                session_item_id=item.id,
                answer_kind=answer.kind,
                answer_json=_encode_answer(answer),
                answer_latex=answer.latex,
                created_at=self._clock(),
            )
            db.add(sub)
            db.flush()  # the unique submission_id stops a concurrent duplicate here
            return _Reservation(sub.id, key, item.id, item_revision, spec, answer)

    def _grade(self, user_id: int, session_id: int, res: _Reservation) -> SubmitView:
        # 3. Grade outside any transaction.
        try:
            checked = self._pool.submit(
                CheckRequest(res.answer_spec, res.answer, request_id=res.submission_id)
            )
        except VerifierBusy:
            self._release(res.submission_pk)
            raise Busy("The checker is busy. Please try again in a moment.") from None
        outcome = checked.outcome
        if isinstance(outcome, FormatIssue):
            self._release(res.submission_pk)  # format issues change nothing (spec 02)
            with self._sessions() as db:
                item = db.get(SessionItem, res.session_item_id)
                assert item is not None
                current = self._current(db, item.session)
                if (
                    current is None
                    or current.id != item.id
                    or item.state is not ItemState.ACTIVE
                    or item.revision != res.expected_revision
                ):
                    raise StaleItem("This problem changed while it was being checked.")
                return SubmitView(outcome, self._view(db, item), replayed=False)
        # 4. Transaction B.
        try:
            with self._tx() as db:
                item = db.get(SessionItem, res.session_item_id)
                assert item is not None
                now = self._clock()
                state, tries = _transition(item.state, item.tries_used, outcome.status)
                changed = db.execute(
                    update(SessionItem)
                    .where(
                        SessionItem.id == item.id,
                        SessionItem.revision == res.expected_revision,
                        SessionItem.state == ItemState.ACTIVE,
                    )
                    .values(state=state, tries_used=tries, revision=SessionItem.revision + 1)
                    .execution_options(synchronize_session=False)
                )
                applied = cast(CursorResult[Any], changed).rowcount == 1
                db.add(
                    AttemptResult(
                        submission_pk=res.submission_pk,
                        status=outcome.status,
                        reason=outcome.reason,
                        method=outcome.method,
                        verifier_version=checked.verifier_version,
                        worker_ms=checked.worker_ms,
                        queue_ms=checked.queue_ms,
                        seconds_on_item=int((now - item.served_at).total_seconds()),
                        counts_as_try=applied and outcome.status is VerdictStatus.INCORRECT,
                        applied=applied,
                    )
                )
                db.flush()
                db.refresh(item)
                view = self._view(db, item)
        except IntegrityError:
            # A concurrent regrade of the same orphan stored its result first.
            replay = self._replay(user_id, session_id, res.submission_id, res.expected_revision)
            if isinstance(replay, SubmitView):
                return replay
            raise StaleItem("This problem changed; reload it.") from None
        if not applied:
            raise StaleItem("This problem changed while it was being checked.")
        return SubmitView(outcome, view, False, checked.worker_ms, checked.queue_ms)

    def _release(self, submission_pk: int) -> None:
        with self._tx() as db:
            db.execute(delete(Submission).where(Submission.id == submission_pk))

    # -- helpers ----------------------------------------------------------------------------

    @contextmanager
    def _tx(self) -> Iterator[Session]:
        """A short write transaction (BEGIN IMMEDIATE). A lock past busy_timeout becomes
        ``DatabaseBusy`` (ruling R12), never a 500."""
        try:
            with write_transaction(self._sessions) as db:
                yield db
        except OperationalError as exc:
            if is_lock_error(exc):
                raise DatabaseBusy("The database is busy. Please try again.") from exc
            raise

    def _owned(self, db: Session, user_id: int, session_id: int) -> StudySession:
        session = db.get(StudySession, session_id)
        if session is None:
            raise NotFound("Session not found.")
        if session.user_id != user_id:
            raise Forbidden("This is not your session.")
        return session

    def _current(self, db: Session, session: StudySession) -> SessionItem | None:
        return db.scalar(
            select(SessionItem)
            .where(SessionItem.session_id == session.id)
            .order_by(SessionItem.sequence.desc())
            .limit(1)
        )

    def _snapshot(self, item: SessionItem) -> Problem:
        """The problem exactly as it was when this presentation was created (review B-A4):
        later content edits, removals or review changes never alter an existing presentation."""
        key = (item.item_id, item.content_version)
        problem = self._snapshots.get(key)
        if problem is None:
            problem = Problem.model_validate(loads_exact(item.problem_json))
            self._snapshots[key] = problem
        return problem

    def _history(self, db: Session, user_id: int) -> History:
        items = db.execute(
            select(SessionItem.id, SessionItem.item_id, SessionItem.served_at)
            .join(StudySession, StudySession.id == SessionItem.session_id)
            .where(StudySession.user_id == user_id)
        ).all()
        results = db.execute(
            select(Submission.session_item_id, AttemptResult.status)
            .join(AttemptResult, AttemptResult.submission_pk == Submission.id)
            .join(SessionItem, SessionItem.id == Submission.session_item_id)
            .join(StudySession, StudySession.id == SessionItem.session_id)
            .where(StudySession.user_id == user_id, AttemptResult.applied.is_(True))
            .order_by(AttemptResult.id)
        ).all()
        latest: dict[int, VerdictStatus] = {}
        for presentation_id, status in results:
            latest[presentation_id] = status
        return [(item_id, latest.get(pk), served_at) for pk, item_id, served_at in items]

    def _done_reason(self, db: Session, session: StudySession) -> str:
        """Why a session ended: nothing left to solve at all, or nothing left for this session."""
        history = self._history(db, session.user_id)
        unsolved = next_item_id(self._content, list(session.topics), history)
        return ALL_CORRECT if unsolved is None else SESSION_COMPLETE

    def _present_next(
        self, db: Session, session: StudySession, sequence: int
    ) -> SessionItem | None:
        shown = set(
            db.scalars(select(SessionItem.item_id).where(SessionItem.session_id == session.id))
        )
        item_id = next_item_id(
            self._content, list(session.topics), self._history(db, session.user_id), shown
        )
        now = self._clock()
        if item_id is None:
            session.ended_at = now
            db.flush()
            return None
        item = SessionItem(
            session_id=session.id,
            item_id=item_id,
            content_version=self._content.versions[item_id],
            problem_json=json.dumps(self._problems[item_id].model_dump(mode="json")),
            sequence=sequence,
            state=ItemState.ACTIVE,
            revision=0,
            served_at=now,
            tries_used=0,
        )
        db.add(item)
        db.flush()
        return item

    def _view(self, db: Session, item: SessionItem) -> ItemView:
        problem = self._snapshot(item)
        answer = problem.answer
        last = db.scalar(
            select(AttemptResult)
            .join(Submission, Submission.id == AttemptResult.submission_pk)
            .where(Submission.session_item_id == item.id, AttemptResult.applied.is_(True))
            .order_by(AttemptResult.id.desc())
            .limit(1)
        )
        return ItemView(
            session_item_id=item.id,
            revision=item.revision,
            state=item.state,
            item_id=item.item_id,
            statement_html=problem.statement_html,
            answer_kind=AnswerKind(answer.kind),
            precision_hint=precision_hint(answer),
            choices=[(c.id, c.latex) for c in answer.choices]
            if isinstance(answer, ChoiceAnswer)
            else None,
            source=problem.source,
            allowed_actions=list(ALLOWED[item.state]),
            tries_left=MAX_TRIES - item.tries_used,
            last_outcome=None if last is None else Verdict(last.status, last.reason, last.method),
            revealed_latex=expected_latex(answer) if item.state is ItemState.REVEALED else None,
        )
