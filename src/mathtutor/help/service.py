"""One help request end to end (spec 06, steps 1-7).

1. Field checks, then one short write transaction (``BEGIN IMMEDIATE``): replay or conflict
   on a known request id; ownership, revision, open state, help-type eligibility and the
   server-owned confusion id; one request in flight per item (else ``PENDING``); the ledger's
   admission and call-1 reservation; a ``pending`` row; ``in_flight`` set. Commit.
2. With no transaction open: context, then ``HelpPipeline.run`` (retrieval, provider calls,
   citation and leak-guard checks, repair, fallback). A second call is reserved first in the
   ledger's own transaction.
3. Settle every reserved call (``mark_uncertain`` when the provider may have billed unknown
   usage; never resent), still outside any transaction.
4. A second short write transaction rechecks ownership, revision, open state, the user's
   privacy epoch, the help sequence and ``in_flight``. Stale: no text is stored and the
   ladder does not move. Otherwise the result is stored, ``help_seq`` advances, and
   ``hint_level`` advances (cap 3) only for a delivered hint. ``in_flight`` is cleared.

Help never changes tries, verdicts or ``SessionItem.revision``. Logs carry status and reason
codes only: never student text, model output, chunk text or the API key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import get_args
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import (
    Conflict,
    DatabaseBusy,
    Forbidden,
    HelpLimited,
    InvalidAction,
    InvalidInput,
    NotFound,
    StaleItem,
)
from mathtutor.application.practice import ItemView, Pool
from mathtutor.content.schema import Problem
from mathtutor.domain import ItemState, VerdictStatus
from mathtutor.help import messages
from mathtutor.help.config import HelpConfig
from mathtutor.help.context import Confusion, HelpContext, HelpType, build_context
from mathtutor.help.leak_guard import LeakStatus
from mathtutor.help.ledger import Ledger
from mathtutor.help.pipeline import HelpPipeline, HelpStatus, PipelineResult, SourceRef
from mathtutor.help.render import render_help_html
from mathtutor.jsonio import loads_exact
from mathtutor.store.db import is_lock_error, write_transaction
from mathtutor.store.models import (
    AttemptResult,
    HelpRequestRow,
    ItemHelpState,
    SessionItem,
    StudySession,
    Submission,
    User,
)

__all__ = [
    "HelpAvailability",
    "HelpIn",
    "HelpOutcome",
    "HelpService",
    "HelpStatus",
    "SourceRef",
]

logger = logging.getLogger(__name__)

HELP_TYPES: tuple[str, ...] = get_args(HelpType)
OPEN_STATES = frozenset({ItemState.ACTIVE, ItemState.EXHAUSTED})
MAX_HINT_LEVEL = 3
MAX_CONFUSION_ID = 64
_TEXT_STATUSES = frozenset({HelpStatus.DELIVERED, HelpStatus.FALLBACK})
_FIXED = {
    HelpStatus.ABSTAINED: messages.ABSTAIN,
    HelpStatus.UNAVAILABLE: messages.UNAVAILABLE,
    HelpStatus.LIMITED: messages.LIMITED,
}


@dataclass(frozen=True)
class HelpIn:
    help_request_id: UUID
    session_item_id: int
    item_revision: int
    help_type: HelpType
    confusion: str | None


@dataclass(frozen=True)
class HelpOutcome:
    request_id: str
    status: HelpStatus
    session_item_id: int
    item_revision: int
    help_seq: int
    hint_level: int | None
    html: str | None
    sources: list[SourceRef]


@dataclass(frozen=True)
class HelpAvailability:
    enabled: bool
    types: list[HelpType]
    confusions: list[Confusion]
    hint_level: int


@dataclass(frozen=True)
class _Admitted:
    request_id: str
    user_id: int
    session_item_id: int
    item_revision: int
    help_type: HelpType
    confusion_label: str | None
    problem: Problem
    hint_level: int | None  # the level this hint is written at; None for other types
    ladder: int  # the item's hint level at admission (the context's level)
    help_seq: int
    entry_id: int


def _payload_hash(user_id: int, req: HelpIn) -> str:
    payload = {
        "user_id": user_id,
        "session_item_id": req.session_item_id,
        "item_revision": req.item_revision,
        "help_type": req.help_type,
        "confusion": req.confusion,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _guard_counts(result: PipelineResult) -> dict[str, int]:
    counts = {s.value: sum(g.counts.get(s, 0) for g in result.guard) for s in LeakStatus}
    counts["blocks"] = sum(1 for g in result.guard if g.decision == "block")
    return counts


def _failed(reason: str) -> PipelineResult:
    return PipelineResult([], HelpStatus.UNAVAILABLE, None, [], [], None, [], reason)


class HelpService:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        cfg: HelpConfig,
        ledger: Ledger,
        pipeline: HelpPipeline,
        pool: Pool,
        confusions: dict[str, list[Confusion]],
        *,
        now: Callable[[], datetime],
        clock: Callable[[], float] = time.monotonic,
        enabled: bool = True,
        slots: threading.BoundedSemaphore | None = None,
    ) -> None:
        """``pool`` grades misconception matches for the context (the grading pool);
        ``clock`` is the monotonic deadline clock shared with the pipeline; ``now`` stamps
        rows. ``slots`` bounds concurrent requests per process (default from the config)."""
        self._sessions = sessions
        self._cfg = cfg
        self._ledger = ledger
        self._pipeline = pipeline
        self._pool = pool
        self._confusions = confusions
        self._now = now
        self._clock = clock
        self._enabled = enabled
        self._slots = slots or threading.BoundedSemaphore(cfg.admission.concurrency)
        self._problems: dict[tuple[str, str], Problem] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    # -- public ------------------------------------------------------------------------------

    def request_help(self, user_id: int, req: HelpIn) -> HelpOutcome:
        rid = str(req.help_request_id)
        started = self._clock()
        deadline = started + self._cfg.deadline_s
        self._validate_fields(req)
        if not self._enabled or not self._slots.acquire(blocking=False):
            # Only new work needs help enabled and a slot; a known id still replays.
            with self._sessions() as db:
                item = self._owned_item(db, user_id, req.session_item_id)
                replay = self._known(db, user_id, rid, req, item)
                if replay is not None:
                    return replay
                state = db.get(ItemHelpState, item.id)
                seq = state.help_seq if state is not None else 0
            return self._plain(rid, req, HelpStatus.UNAVAILABLE, seq)
        try:
            return self._serve(user_id, rid, req, started, deadline)
        finally:
            self._slots.release()

    def availability(self, item_view: ItemView, user_id: int) -> HelpAvailability:
        with self._sessions() as db:
            item = self._owned_item(db, user_id, item_view.session_item_id)
            state = db.get(ItemHelpState, item.id)
            problem = self._problem(item)
            confusions = list(self._confusions.get(problem.topic, []))
            types: list[HelpType] = []
            if self._enabled and item.state in OPEN_STATES:
                types.append("hint")
                if self._latest_status(db, item) is VerdictStatus.INCORRECT:
                    types.append("feedback")
                if confusions:
                    types.append("explain")
        level = state.hint_level if state is not None else 1
        return HelpAvailability(self._enabled, types, confusions, level)

    # -- the request -------------------------------------------------------------------------

    def _serve(
        self, user_id: int, rid: str, req: HelpIn, started: float, deadline: float
    ) -> HelpOutcome:
        try:
            with self._tx() as db:
                admitted = self._admit(db, user_id, rid, req)
        except HelpLimited as limited:
            logger.info("help limited reason=%s", limited.reason)
            return self._plain(rid, req, HelpStatus.LIMITED, self._peek(user_id, req))
        if isinstance(admitted, HelpOutcome):
            return admitted
        entries = {1: admitted.entry_id}
        result = self._work(admitted, deadline, entries)
        self._settle(result, entries)
        outcome = self._finalize(admitted, result, started)
        logger.info(
            "help finished status=%s reason=%s calls=%d",
            outcome.status.value,
            result.reason,
            len(result.calls),
        )
        return outcome

    def _work(
        self, admitted: _Admitted, deadline: float, entries: dict[int, int]
    ) -> PipelineResult:
        if self._clock() >= deadline:
            return _failed("deadline")
        try:
            ctx = self._build_context(admitted)
        except Exception as exc:  # noqa: BLE001 - fail closed; log the type only
            logger.warning("help context error: %s", type(exc).__name__)
            return _failed("context_error")
        if self._clock() >= deadline:
            return _failed("deadline")
        return self._pipeline.run(
            ctx,
            admitted.help_type,
            admitted.confusion_label,
            admitted.problem.answer,
            deadline,
            may_call=lambda n: self._reserve(admitted, n, entries),
        )

    def _build_context(self, admitted: _Admitted) -> HelpContext:
        """Reads the item and may call the grading pool: no write transaction is open."""
        with self._sessions() as db:
            item = db.get(SessionItem, admitted.session_item_id)
            if item is None:
                raise NotFound(messages.PROBLEM_NOT_FOUND)
            return build_context(db, item, admitted.problem, admitted.ladder, self._pool)

    def _reserve(self, admitted: _Admitted, call_no: int, entries: dict[int, int]) -> bool:
        """Reserve a later call in the ledger's own transaction; refusal ends the run."""
        try:
            entries[call_no] = self._ledger.reserve_call(
                admitted.request_id, admitted.user_id, call_no, self._cfg.model
            )
        except HelpLimited:
            return False
        except OperationalError as exc:
            logger.warning("help reserve failed: %s", type(exc).__name__)
            return False
        return True

    def _settle(self, result: PipelineResult, entries: dict[int, int]) -> None:
        """Settle each reserved call; unknown usage stays counted at its worst case."""
        calls = {c.call_no: c for c in result.calls}
        for call_no, entry_id in sorted(entries.items()):
            call = calls.get(call_no)
            try:
                if call is None:  # reserved, never sent
                    self._ledger.settle(entry_id, 0, 0)
                elif call.billed_unknown:
                    self._ledger.mark_uncertain(entry_id)
                elif call.input_tokens is not None and call.output_tokens is not None:
                    self._ledger.settle(entry_id, call.input_tokens, call.output_tokens)
                elif call.outcome.startswith("error_"):  # refused before any work was billed
                    self._ledger.settle(entry_id, 0, 0)
                else:  # a reply without usage: billed, amount unknown
                    self._ledger.mark_uncertain(entry_id)
            except (ValueError, OperationalError) as exc:
                logger.warning("help settle failed: %s", type(exc).__name__)

    # -- transaction 1: admission ------------------------------------------------------------

    def _admit(self, db: Session, user_id: int, rid: str, req: HelpIn) -> HelpOutcome | _Admitted:
        item = self._owned_item(db, user_id, req.session_item_id)
        replay = self._known(db, user_id, rid, req, item)
        if replay is not None:
            return replay
        payload = _payload_hash(user_id, req)
        problem = self._problem(item)
        label = self._validate(db, item, req, problem)
        user = db.get(User, user_id)
        if user is None:
            raise NotFound(messages.USER_NOT_FOUND)
        state = db.get(ItemHelpState, item.id)
        if state is None:
            state = ItemHelpState(session_item_id=item.id, hint_level=1, help_seq=0)
            db.add(state)
            db.flush()
        if state.in_flight is not None and not self._abandon(db, state):
            return HelpOutcome(
                state.in_flight, HelpStatus.PENDING, item.id, item.revision, state.help_seq,
                None, None, [],
            )  # fmt: skip
        entry_id = self._ledger.admit(db, user_id, rid, self._cfg.model)
        level = state.hint_level if req.help_type == "hint" else None
        db.add(
            HelpRequestRow(
                request_id=rid,
                user_id=user_id,
                session_item_id=item.id,
                item_revision=item.revision,
                help_type=req.help_type,
                confusion_id=req.confusion,
                payload_hash=payload,
                privacy_epoch=user.privacy_epoch,
                help_seq=state.help_seq,
                hint_level=level,
                status=HelpStatus.PENDING.value,
                reason=None,
                model=self._cfg.model,
                prompt_version=self._cfg.prompt_version,
                corpus_hash=self._pipeline.corpus_hash,
                index_fingerprint=self._pipeline.index_fingerprint,
                retrieved_ids=[],
                cited_ids=[],
                guard_counts={},
                calls=0,
                latency_ms=None,
                arm="none",
                serving_model=None,
                output_json=None,
                created_at=self._now(),
                finished_at=None,
                cleared_at=None,
                next_submission_id=None,
            )
        )
        state.in_flight = rid
        db.flush()
        return _Admitted(
            rid, user_id, item.id, item.revision, req.help_type, label, problem, level,
            state.hint_level, state.help_seq, entry_id,
        )  # fmt: skip

    def _abandon(self, db: Session, state: ItemHelpState) -> bool:
        """Free an item whose in-flight request is older than ``uncertain_after_s``: its worker
        died (any live request ends by the deadline). If it ever finishes, it finalizes as
        stale. Returns False while the in-flight request may still be running."""
        old = db.scalar(select(HelpRequestRow).where(HelpRequestRow.request_id == state.in_flight))
        if old is not None and old.status == HelpStatus.PENDING.value:
            if not self._expired(old):
                return False
            self._mark_abandoned(old)
        state.in_flight = None
        return True

    def _expired(self, row: HelpRequestRow) -> bool:
        """A pending request older than ``uncertain_after_s`` (R21): its worker is gone."""
        age = self._now() - row.created_at
        return age >= timedelta(seconds=self._cfg.admission.uncertain_after_s)

    def _mark_abandoned(self, row: HelpRequestRow) -> None:
        row.status = HelpStatus.UNAVAILABLE.value
        row.reason = "abandoned"
        row.output_json = None
        row.finished_at = self._now()

    def _known(
        self, db: Session, user_id: int, rid: str, req: HelpIn, item: SessionItem
    ) -> HelpOutcome | None:
        """The replay of an already-used request id, or None for a new id. Read-only."""
        row = db.scalar(select(HelpRequestRow).where(HelpRequestRow.request_id == rid))
        if row is None:
            return None
        if row.user_id != user_id or row.payload_hash != _payload_hash(user_id, req):
            raise Conflict(messages.ID_REUSED)
        return self._replay(db, row, item)

    def _replay(self, db: Session, row: HelpRequestRow, item: SessionItem) -> HelpOutcome:
        """A known request id with the same payload: pending (or, past ``uncertain_after_s``,
        its abandoned outcome), or its stored result while the presentation and the privacy
        epoch are unchanged, else stale (no text)."""
        status = HelpStatus(row.status)
        if status is HelpStatus.PENDING:
            if self._expired(row):
                return self._outcome(row, HelpStatus.UNAVAILABLE, None, [])
            return self._outcome(row, status, None, [])
        user = db.get(User, row.user_id)
        valid = (
            user is not None
            and user.privacy_epoch == row.privacy_epoch
            and row.cleared_at is None
            and item.revision == row.item_revision
        )
        if status is HelpStatus.STALE or not valid:
            return self._outcome(row, HelpStatus.STALE, None, [])
        text: str | None = None
        sources: list[SourceRef] = []
        if row.output_json is not None:
            data = loads_exact(row.output_json)
            text = str(data["text"])
            sources = [SourceRef(**s) for s in data["sources"]]
        return self._outcome(row, status, text, sources)

    # -- transaction 2: finalization ---------------------------------------------------------

    def _finalize(self, admitted: _Admitted, result: PipelineResult, started: float) -> HelpOutcome:
        rid = admitted.request_id
        latency = max(0, round((self._clock() - started) * 1000))
        try:
            with self._tx() as db:
                row = db.scalar(select(HelpRequestRow).where(HelpRequestRow.request_id == rid))
                item = db.get(SessionItem, admitted.session_item_id)
                state = db.get(ItemHelpState, admitted.session_item_id)
                user = db.get(User, admitted.user_id)
                session = db.get(StudySession, item.session_id) if item is not None else None
                pending = row is not None and row.status == HelpStatus.PENDING.value
                if row is not None and pending and self._expired(row):
                    # Finished after the abandonment window: replays already report it
                    # unavailable, so it stays that way and stores nothing.
                    self._mark_abandoned(row)
                    pending = False
                fresh = (
                    pending
                    and row is not None
                    and item is not None
                    and session is not None
                    and session.user_id == admitted.user_id
                    and item.revision == admitted.item_revision
                    and item.state in OPEN_STATES
                    and user is not None
                    and user.privacy_epoch == row.privacy_epoch
                    and state is not None
                    and state.help_seq == admitted.help_seq
                    and state.in_flight == rid
                )
                if row is not None and pending:
                    row.calls = len(result.calls)
                    row.retrieved_ids = list(result.retrieved_ids)
                    row.cited_ids = list(result.cited_ids)
                    row.guard_counts = _guard_counts(result)
                    row.latency_ms = latency
                    row.serving_model = result.calls[-1].model if result.calls else None
                    row.finished_at = self._now()
                if not fresh or row is None or state is None:
                    if row is not None and pending:
                        row.status = HelpStatus.STALE.value
                        row.reason = "stale"
                        row.output_json = None
                    if state is not None and state.in_flight == rid:
                        state.in_flight = None
                    seq = state.help_seq if state is not None else admitted.help_seq
                    return self._stale(admitted, seq)
                state.help_seq += 1
                if result.status is HelpStatus.DELIVERED and admitted.help_type == "hint":
                    state.hint_level = min(state.hint_level + 1, MAX_HINT_LEVEL)
                state.in_flight = None
                row.status = result.status.value
                row.reason = result.reason[:32]
                row.help_seq = state.help_seq
                if result.status in _TEXT_STATUSES and result.text is not None:
                    row.output_json = json.dumps(
                        {"text": result.text, "sources": [asdict(s) for s in result.sources]}
                    )
                text = result.text if result.status in _TEXT_STATUSES else None
                return self._outcome(row, result.status, text, list(result.sources))
        except (OperationalError, DatabaseBusy) as exc:
            # The item stays in flight until ``_abandon`` frees it; nothing is delivered.
            logger.warning("help finalize failed: %s", type(exc).__name__)
            return HelpOutcome(
                rid, HelpStatus.UNAVAILABLE, admitted.session_item_id, admitted.item_revision,
                admitted.help_seq, admitted.hint_level, render_help_html(messages.UNAVAILABLE),
                [],
            )  # fmt: skip

    # -- helpers -----------------------------------------------------------------------------

    def _validate_fields(self, req: HelpIn) -> None:
        if req.help_type not in HELP_TYPES:
            raise InvalidInput(messages.UNKNOWN_HELP_TYPE, code="unknown_help_type")
        if req.help_type == "explain":
            if not isinstance(req.confusion, str) or not 0 < len(req.confusion) <= (
                MAX_CONFUSION_ID
            ):
                raise InvalidInput(messages.CHOOSE_CONFUSION, code="unknown_confusion")
        elif req.confusion is not None:
            raise InvalidInput(messages.CONFUSION_ONLY_EXPLAIN, code="unknown_confusion")

    def _validate(
        self, db: Session, item: SessionItem, req: HelpIn, problem: Problem
    ) -> str | None:
        """Presentation and eligibility checks; returns the confusion label for explain."""
        if item.revision != req.item_revision:
            raise StaleItem(messages.PROBLEM_CHANGED)
        if item.state not in OPEN_STATES:
            raise InvalidAction(messages.HELP_CLOSED, code="help_closed")
        if req.help_type == "feedback" and self._latest_status(db, item) is not (
            VerdictStatus.INCORRECT
        ):
            raise InvalidAction(messages.FEEDBACK_NEEDS_WRONG, code="no_wrong_attempt")
        if req.help_type == "explain":
            by_id = {c.id: c.label for c in self._confusions.get(problem.topic, [])}
            label = by_id.get(req.confusion or "")
            if label is None:
                raise InvalidInput(messages.CHOOSE_CONFUSION, code="unknown_confusion")
            return label
        return None

    @staticmethod
    def _latest_status(db: Session, item: SessionItem) -> VerdictStatus | None:
        """The latest applied (consumed) verdict on the item."""
        return db.scalar(
            select(AttemptResult.status)
            .join(Submission, Submission.id == AttemptResult.submission_pk)
            .where(Submission.session_item_id == item.id, AttemptResult.applied.is_(True))
            .order_by(AttemptResult.id.desc())
            .limit(1)
        )

    @staticmethod
    def _owned_item(db: Session, user_id: int, session_item_id: int) -> SessionItem:
        item = db.get(SessionItem, session_item_id)
        if item is None:
            raise NotFound(messages.PROBLEM_NOT_FOUND)
        session = db.get(StudySession, item.session_id)
        if session is None or session.user_id != user_id:
            raise Forbidden(messages.NOT_YOUR_PROBLEM)
        return item

    def _peek(self, user_id: int, req: HelpIn) -> int:
        """The item's help sequence, after the ownership check (for statuses with no row)."""
        with self._sessions() as db:
            item = self._owned_item(db, user_id, req.session_item_id)
            state = db.get(ItemHelpState, item.id)
            return state.help_seq if state is not None else 0

    def _problem(self, item: SessionItem) -> Problem:
        """The problem exactly as presented (the item's snapshot), never newer content."""
        key = (item.item_id, item.content_version)
        problem = self._problems.get(key)
        if problem is None:
            problem = Problem.model_validate(loads_exact(item.problem_json))
            self._problems[key] = problem
        return problem

    def _plain(self, rid: str, req: HelpIn, status: HelpStatus, help_seq: int) -> HelpOutcome:
        html = render_help_html(_FIXED[status]) if status in _FIXED else None
        return HelpOutcome(
            rid, status, req.session_item_id, req.item_revision, help_seq, None, html, []
        )

    def _stale(self, admitted: _Admitted, help_seq: int) -> HelpOutcome:
        return HelpOutcome(
            admitted.request_id, HelpStatus.STALE, admitted.session_item_id,
            admitted.item_revision, help_seq, admitted.hint_level, None, [],
        )  # fmt: skip

    @staticmethod
    def _outcome(
        row: HelpRequestRow, status: HelpStatus, text: str | None, sources: list[SourceRef]
    ) -> HelpOutcome:
        if status in _TEXT_STATUSES and text is not None:
            html: str | None = render_help_html(text)
        elif status in _FIXED:
            html = render_help_html(_FIXED[status])
        else:
            html = None
        return HelpOutcome(
            row.request_id, status, row.session_item_id, row.item_revision, row.help_seq,
            row.hint_level, html, sources if html is not None else [],
        )  # fmt: skip

    @contextmanager
    def _tx(self) -> Iterator[Session]:
        """A short write transaction; a lock past busy_timeout becomes ``DatabaseBusy``."""
        try:
            with write_transaction(self._sessions) as db:
                yield db
        except OperationalError as exc:
            if is_lock_error(exc):
                raise DatabaseBusy(messages.DATABASE_BUSY) from exc
            raise
