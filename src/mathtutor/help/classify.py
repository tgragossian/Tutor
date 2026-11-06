"""The background mistake classifier (spec D5): label every applied wrong answer.

After an applied incorrect verdict, ``PracticeService`` hands the answer id to ``submit``. One
daemon worker thread takes ids from a bounded queue (``queue_max``; more are dropped, and the
classifying hint labels those later) and runs ``classify``:

1. One short write transaction: the answer must be applied, incorrect and unlabeled, with no
   earlier classify entry; the ledger admits ``classify-<answer id>`` (``kind="classify"``:
   inside the month budget, outside the per-user help limits). Commit.
2. One provider call with no transaction open. Never retried.
3. Settle the call in the ledger (``mark_uncertain`` when the provider may have billed
   unknown usage).
4. A valid label is written with ``set_mistake_type`` (write-once): if a classifying hint
   labeled the answer first, that label stays.

Any failure leaves ``mistake_type`` NULL. Logs carry reason codes and error types only: never
student text, model output or the key.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.errors import HelpLimited
from mathtutor.application.practice import expected_latex
from mathtutor.content.schema import ChoiceAnswer, Problem
from mathtutor.domain import VerdictStatus
from mathtutor.help.config import HelpConfig
from mathtutor.help.generator import (
    CLASSIFY_SCHEMA,
    GenerationRequest,
    GenerationResult,
    Generator,
    GeneratorError,
    MistakeType,
)
from mathtutor.help.ledger import Ledger
from mathtutor.help.prompts import build_classify_prompt
from mathtutor.store.answers import set_mistake_type
from mathtutor.store.db import write_transaction
from mathtutor.store.models import Answer, SessionItem, UsageEntry

logger = logging.getLogger(__name__)

KIND = "classify"
_CLOSE_GRACE_S = 5.0  # beyond one call's timeout, for the settle and label writes


class ClassifyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mistake_type: MistakeType


def request_id(answer_id: int) -> str:
    return f"classify-{answer_id}"


class MistakeClassifier:
    def __init__(
        self,
        sessions: sessionmaker[Session],
        cfg: HelpConfig,
        ledger: Ledger,
        generator: Generator,
        problem_of: Callable[[SessionItem], Problem],
    ) -> None:
        """``problem_of`` returns the problem as presented (the item's snapshot)."""
        self._sessions = sessions
        self._cfg = cfg
        self._params = cfg.classifier
        self._ledger = ledger
        self._generator = generator
        self._problem_of = problem_of
        self._queue: queue.Queue[int | None] = queue.Queue(maxsize=self._params.queue_max)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._closed = False

    # -- background --------------------------------------------------------------------------

    def submit(self, answer_id: int) -> None:
        """Queue an answer for the worker; never blocks. Dropped when full or closed."""
        with self._lock:
            if self._closed:
                return
            if self._thread is None:
                self._thread = threading.Thread(
                    target=self._run, name="mistake-classifier", daemon=True
                )
                self._thread.start()
            try:
                self._queue.put_nowait(answer_id)
            except queue.Full:
                logger.info("classify dropped reason=queue_full")

    def close(self) -> None:
        """Stop the worker: answers still waiting are dropped (they stay NULL); a call in
        progress may finish, bounded by its timeout. Idempotent."""
        with self._lock:
            self._closed = True
            thread = self._thread
            while True:
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
            if thread is not None:
                # The stop sentinel. The queue was just emptied and submit is shut: there is room.
                self._queue.put_nowait(None)
        if thread is not None:
            thread.join(self._params.timeout_s + _CLOSE_GRACE_S)
            if thread.is_alive():
                logger.warning("classify worker still running at close")

    def _run(self) -> None:
        while True:
            answer_id = self._queue.get()
            if answer_id is None:  # close()
                return
            try:
                self.classify(answer_id)
            except Exception as exc:  # noqa: BLE001 - the worker must outlive any one answer
                logger.warning("classify failed: %s", type(exc).__name__)

    # -- one answer --------------------------------------------------------------------------

    def classify(self, answer_id: int) -> str | None:
        """Label one answer synchronously. Returns the label this call wrote, else None."""
        rid = request_id(answer_id)
        params = self._params
        try:
            with write_transaction(self._sessions) as db:
                found = self._prompt(db, answer_id, rid)
                if found is None:
                    return None
                user_id, (system, user) = found
                entry_id = self._ledger.admit(db, user_id, rid, params.model, kind=KIND)
        except HelpLimited as limited:
            logger.info("classify skipped reason=%s", limited.reason)
            return None
        except IntegrityError:  # a concurrent classify of the same answer reserved first
            logger.info("classify skipped reason=duplicate")
            return None
        req = GenerationRequest(
            model=params.model,
            effort=params.effort,
            system=system,
            user=user,
            schema=CLASSIFY_SCHEMA,
            max_output_tokens=params.max_output_tokens,
            timeout_s=params.timeout_s,
        )
        result = self._call(req, entry_id)
        if result is None:
            return None
        label = self._label(result)
        if label is None:
            logger.info("classify failed reason=bad_reply stop=%s", result.stop_reason)
            return None
        with write_transaction(self._sessions) as db:
            written = set_mistake_type(db, answer_id, label)
        logger.info("classify finished written=%s", written)
        return label if written else None

    def _prompt(self, db: Session, answer_id: int, rid: str) -> tuple[int, tuple[str, str]] | None:
        """The user id and prompt, or None when the answer is not ours to label."""
        answer = db.get(Answer, answer_id)
        if (
            answer is None
            or answer.applied is not True
            or answer.status is not VerdictStatus.INCORRECT
            or answer.mistake_type is not None
        ):
            return None
        if db.scalar(select(UsageEntry.id).where(UsageEntry.request_id == rid).limit(1)):
            return None  # one call per answer, ever
        problem = self._problem_of(answer.session_item)
        spec = problem.answer
        if isinstance(spec, ChoiceAnswer):
            choices = {c.id: c.latex for c in spec.choices}
            attempt = choices.get(answer.choice_id or "", "")
        else:
            attempt = answer.latex or ""
        prompt = build_classify_prompt(problem.statement, expected_latex(spec), attempt, self._cfg)
        return answer.user_id, prompt

    def _call(self, req: GenerationRequest, entry_id: int) -> GenerationResult | None:
        """One call, then its settlement; None when the call failed."""
        try:
            result = self._generator.generate(req)
        except GeneratorError as exc:
            logger.info("classify failed reason=%s", exc.kind)
            if exc.billed_unknown:
                self._ledger.mark_uncertain(entry_id)
            else:
                self._ledger.settle(entry_id, 0, 0)
            return None
        except Exception as exc:  # noqa: BLE001 - an unknown failure may still have billed
            logger.warning("classify failed: %s", type(exc).__name__)
            self._ledger.mark_uncertain(entry_id)
            return None
        if result.input_tokens is not None and result.output_tokens is not None:
            self._ledger.settle(entry_id, result.input_tokens, result.output_tokens)
        else:  # a reply without usage: billed, amount unknown
            self._ledger.mark_uncertain(entry_id)
        return result

    @staticmethod
    def _label(result: GenerationResult) -> str | None:
        if result.text is None:
            return None
        try:
            return ClassifyOutput.model_validate(json.loads(result.text)).mistake_type
        except ValueError:  # not JSON, or not one label (pydantic's error is a ValueError)
            return None
