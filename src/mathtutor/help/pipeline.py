"""The help path after the context is built: retrieval, prompt, provider call(s), checks.

``HelpPipeline.run`` touches neither the database nor the ledger (ruling R4): it reports each
provider call's usage in a ``CallRecord`` and the caller settles it. ``HelpService`` wraps it
with admission and finalization; the evaluation harness calls it directly.

At most ``cfg.max_calls`` (2) provider calls per run, all repair reasons combined. A reply is
used only if it parses as ``HelpOutput``, cites only this run's retrieved passages and passes
the leak guard; otherwise one strict repair call is made when the budget hook allows it, and
then a fixed nudge for the top passage's section. A ``GeneratorError`` is never retried.
Nothing here logs or raises student text, model output or chunk text.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum

from pydantic import ValidationError

from mathtutor.content.schema import Answer, ChoiceAnswer
from mathtutor.help import messages
from mathtutor.help.config import MAX_CALLS, HelpConfig
from mathtutor.help.context import HelpContext, HelpType
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    HINT_CHOICE_SCHEMA,
    GenerationRequest,
    GenerationResult,
    Generator,
    GeneratorError,
    HelpOutput,
    HintChoiceOutput,
    UncitedHelpOutput,
)
from mathtutor.help.leak_guard import GuardResult, LeakGuard, MalformedMath, split_spans
from mathtutor.help.prompts import build_prompt
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import LICENCE, Chunk, ChunkRole, Corpus
from mathtutor.retrieval.query import build_query

logger = logging.getLogger(__name__)

BOOK = "Calculus Volume 1"
MIN_SUBSTRING_ANSWER = 5
_SPACE = re.compile(r"\s+")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")  # every C0/C1 control but \t and \n


class HelpStatus(StrEnum):
    DELIVERED = "delivered"
    ABSTAINED = "abstained"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"
    LIMITED = "limited"
    STALE = "stale"
    PENDING = "pending"


@dataclass(frozen=True)
class SourceRef:
    label: str
    url: str
    license: str


@dataclass(frozen=True)
class CallRecord:
    """One provider call: usage for settlement and a content-free outcome code."""

    call_no: int
    model: str
    input_tokens: int | None
    output_tokens: int | None
    billed_unknown: bool  # the provider may have billed; usage unknown (never resend)
    outcome: str
    latency_ms: int | None


@dataclass(frozen=True)
class PipelineResult:
    calls: list[CallRecord]
    status: HelpStatus
    text: str | None
    cited_ids: list[str]
    guard: list[GuardResult]
    top_section: str | None
    retrieved_ids: list[str] = field(default_factory=list)
    reason: str = ""
    sources: list[SourceRef] = field(default_factory=list)
    mistake_type: str | None = None  # the model's mistake type on a classifying hint (R35)


def source_ref(chunk: Chunk) -> SourceRef:
    return SourceRef(f"{BOOK}, {chunk.section} {chunk.section_title}", chunk.url, LICENCE)


def answer_latex(answer: Answer) -> str:
    """The reference answer as LaTeX: the correct choice's formula for choice problems."""
    if isinstance(answer, ChoiceAnswer):
        return next((c.latex for c in answer.choices if c.id == answer.correct), "")
    return answer.latex


def _squash(text: str) -> str:
    return _SPACE.sub("", text)


def _shows_answer(text: str, secret: str) -> bool:
    """Ruling R23: an answer of at least ``MIN_SUBSTRING_ANSWER`` characters (whitespace
    removed) matches as a substring; a shorter one (``2``, ``x``) only as a whole math span,
    so it cannot empty retrieval by matching every passage that mentions a digit."""
    if not secret:
        return False
    if len(secret) >= MIN_SUBSTRING_ANSWER:
        return secret in _squash(text)
    try:
        spans = split_spans(text)
    except MalformedMath:
        return secret in _squash(text)  # unreadable math: fall back to the strict test
    return any(kind != "prose" and _squash(body) == secret for kind, body in spans)


class _Invalid(Exception):
    """A reply that cannot be delivered; ``reason`` is a fixed code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class HelpPipeline:
    def __init__(
        self,
        cfg: HelpConfig,
        corpus: Corpus,
        index: Bm25Index,
        generator: Generator,
        guard: LeakGuard,
        clock: Callable[[], float],
        *,
        no_passages: bool = False,
    ) -> None:
        """``no_passages`` is the evaluation-only generator baseline (review C1-R7): no
        retrieval, the ``no_passages`` prompt addendum and uncited replies, with the same model,
        limits, repair and leak guard. Production never sets it."""
        self._no_passages = no_passages
        self._cfg = cfg
        self._corpus = corpus
        self._index = index
        self._generator = generator
        self._guard = guard
        self._clock = clock
        self._roles = frozenset(ChunkRole(r) for r in cfg.retrieval.roles)

    @property
    def corpus_hash(self) -> str:
        return self._corpus.corpus_hash

    @property
    def index_fingerprint(self) -> str:
        return self._index.fingerprint

    def retrieve(
        self, ctx: HelpContext, help_type: HelpType, confusion_label: str | None, answer: Answer
    ) -> list[Chunk]:
        """Top passages in the allowed roles, minus any that show the answer (R23)."""
        query = build_query(ctx, help_type, confusion_label, self._cfg.retrieval)
        hits = self._index.search(
            query, self._cfg.passages, boost_section=ctx.section, roles=self._roles
        )
        secret = _squash(answer_latex(answer))
        chunks = [self._corpus.chunks[h.chunk_id] for h in hits]
        return [c for c in chunks if not _shows_answer(c.text, secret)]

    def run(
        self,
        ctx: HelpContext,
        help_type: HelpType,
        confusion_label: str | None,
        answer: Answer,
        deadline: float,
        *,
        may_call: Callable[[int], bool] | None = None,
        hint_levels: Mapping[str, int] | None = None,
    ) -> PipelineResult:
        """``deadline`` is on the pipeline clock's scale. ``may_call(n)`` is asked before each
        call after the first (the caller reserves its cost); False ends the run with the
        fallback. ``hint_levels``: a hint on a wrong attempt not yet classified; the model names
        its mistake type and writes at that type's level (``result.mistake_type``, R35). Never
        raises: an unexpected error is ``UNAVAILABLE``."""
        calls: list[CallRecord] = []
        guards: list[GuardResult] = []
        chunks: list[Chunk] = []
        try:
            return self._run(
                ctx,
                help_type,
                confusion_label,
                answer,
                deadline,
                may_call,
                calls,
                guards,
                chunks,
                hint_levels,
            )
        except Exception as exc:  # noqa: BLE001 - fail closed; log the type only
            logger.warning("help pipeline error: %s", type(exc).__name__)
            return PipelineResult(
                calls,
                HelpStatus.UNAVAILABLE,
                None,
                [],
                guards,
                chunks[0].section if chunks else None,
                [c.chunk_id for c in chunks],
                "internal_error",
            )

    def _run(
        self,
        ctx: HelpContext,
        help_type: HelpType,
        confusion_label: str | None,
        answer: Answer,
        deadline: float,
        may_call: Callable[[int], bool] | None,
        calls: list[CallRecord],
        guards: list[GuardResult],
        chunks: list[Chunk],
        hint_levels: Mapping[str, int] | None = None,
    ) -> PipelineResult:
        def result(
            status: HelpStatus,
            reason: str,
            text: str | None = None,
            cited: list[str] | None = None,
            mistake_type: str | None = None,
        ) -> PipelineResult:
            by_id = {c.chunk_id: c for c in chunks}
            if status is HelpStatus.DELIVERED:
                refs = [source_ref(by_id[i]) for i in cited or []]
            elif status is HelpStatus.FALLBACK and chunks:
                refs = [source_ref(chunks[0])]
            else:
                refs = []
            return PipelineResult(
                list(calls),
                status,
                text,
                list(cited or []),
                list(guards),
                chunks[0].section if chunks else None,
                [c.chunk_id for c in chunks],
                reason,
                list(dict.fromkeys(refs)),
                mistake_type,
            )

        def fallback(reason: str) -> PipelineResult:
            if not chunks:  # no relevant section to point to (the no-passage baseline)
                return result(HelpStatus.UNAVAILABLE, reason)
            section = f"Section {chunks[0].section}"
            return result(HelpStatus.FALLBACK, reason, messages.NUDGE.format(section=section))

        if self._clock() >= deadline:
            return result(HelpStatus.UNAVAILABLE, "deadline")
        if not self._no_passages:
            chunks.extend(self.retrieve(ctx, help_type, confusion_label, answer))
            if not chunks:
                return result(HelpStatus.ABSTAINED, "no_hits")
        allowed = {c.chunk_id for c in chunks}

        reason = ""
        max_calls = min(max(self._cfg.max_calls, 1), MAX_CALLS)  # never more than two
        for call_no in range(1, max_calls + 1):
            if call_no > 1 and (may_call is not None and not may_call(call_no)):
                return fallback("budget")
            remaining = deadline - self._clock()
            if remaining <= 0:
                return fallback("deadline") if calls else result(HelpStatus.UNAVAILABLE, "deadline")
            try:
                system, user = build_prompt(
                    ctx,
                    help_type,
                    chunks,
                    confusion_label,
                    call_no > 1,
                    cfg=self._cfg,
                    no_passages=self._no_passages,
                    hint_levels=hint_levels,
                )
            except ValueError:
                return result(HelpStatus.UNAVAILABLE, "prompt_budget")
            req = GenerationRequest(
                model=self._cfg.model,
                effort=self._cfg.effort,
                system=system,
                user=user,
                schema=HINT_CHOICE_SCHEMA if hint_levels is not None else HELP_OUTPUT_SCHEMA,
                max_output_tokens=self._cfg.max_output_tokens,
                timeout_s=remaining,
            )
            # Recorded as sent with unknown usage before the provider is contacted (review
            # C1-R3): if anything unexpected happens from here on, the caller keeps the
            # reservation as uncertain instead of releasing it. Replaced below once known.
            calls.append(CallRecord(call_no, req.model, None, None, True, "dispatched", None))
            try:
                reply = self._generator.generate(req)
            except GeneratorError as err:
                unknown = err.billed_unknown or err.status_code == 504
                calls[-1] = CallRecord(
                    call_no, req.model, None, None, unknown, f"error_{err.kind}", None
                )
                return result(HelpStatus.UNAVAILABLE, f"generator_{err.kind}")
            # Usage recorded before any check, so an unexpected error later in this call
            # still reports what the provider billed.
            calls[-1] = self._record(call_no, reply, "received")
            try:
                out = self._parse(reply, allowed, hint_levels is not None)
                if not out.abstain:
                    self._check(out.text, answer, deadline, guards)
            except _Invalid as bad:
                calls[-1] = replace(calls[-1], outcome=bad.reason)
                reason = bad.reason
                if bad.reason == "deadline":
                    return fallback("deadline")
                continue
            if out.abstain:  # its text and ids are never delivered
                calls[-1] = replace(calls[-1], outcome="abstain")
                return result(HelpStatus.ABSTAINED, "abstained")
            calls[-1] = replace(calls[-1], outcome="ok")
            kind = out.mistake_type if isinstance(out, HintChoiceOutput) else None
            return result(HelpStatus.DELIVERED, "delivered", out.text, list(out.source_ids), kind)
        return fallback(reason)

    @staticmethod
    def _record(call_no: int, reply: GenerationResult, outcome: str) -> CallRecord:
        return CallRecord(
            call_no,
            reply.model,
            reply.input_tokens,
            reply.output_tokens,
            False,
            outcome,
            reply.latency_ms,
        )

    def _parse(
        self, reply: GenerationResult, allowed: set[str], classify: bool = False
    ) -> HelpOutput | UncitedHelpOutput:
        if reply.text is None:
            raise _Invalid(f"invalid_{reply.stop_reason}"[:32])
        shape: type[HelpOutput] | type[UncitedHelpOutput]
        if self._no_passages:
            shape = UncitedHelpOutput
        elif classify:
            shape = HintChoiceOutput
        else:
            shape = HelpOutput
        try:
            out = shape.model_validate_json(reply.text)
        except ValidationError:
            raise _Invalid("invalid_schema") from None
        if out.abstain:
            return out
        if _CONTROL.search(out.text):
            # The guard and the renderer must read the same spans; no NULs or other controls.
            raise _Invalid("invalid_control_char")
        if len(out.text) > self._cfg.max_output_chars or len(out.source_ids) > (
            self._cfg.max_source_ids
        ):
            raise _Invalid("invalid_schema")
        if not set(out.source_ids) <= allowed:
            raise _Invalid("invalid_citation")
        return out

    def _check(self, text: str, answer: Answer, deadline: float, guards: list[GuardResult]) -> None:
        if self._clock() >= deadline:
            raise _Invalid("deadline")
        verdict = self._guard.check(text, answer, deadline)
        guards.append(verdict)
        if verdict.decision == "block":
            raise _Invalid(f"invalid_guard_{verdict.reason}"[:32])
        if self._clock() >= deadline:  # the guard returned too late: never deliver (C1-R5)
            raise _Invalid("deadline")
