"""A HelpService over a real SQLite file, a scripted generator, fake pools and fake clocks.

One problem (openstax-c1-3.6-221, chain rule, answer ``18x(3x^2+1)^2``) and a tiny synthetic
corpus, so retrieval and the hit filter are fully under the test's control.
"""

from __future__ import annotations

import dataclasses
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from mathtutor.application.auth import AuthService
from mathtutor.application.practice import ItemView, PracticeService
from mathtutor.content.loader import LoadedContent, load_bundle
from mathtutor.domain import AnswerKind, Method, VerdictReason, VerdictStatus
from mathtutor.help.config import DEFAULT_CONFIG_PATH, HelpConfig, load_help_config
from mathtutor.help.context import Confusion, HelpType, load_confusions
from mathtutor.help.generator import (
    GenerationRequest,
    GenerationResult,
    GeneratorError,
    ScriptedGenerator,
)
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.help.ledger import Ledger
from mathtutor.help.pipeline import HelpPipeline
from mathtutor.help.service import HelpIn, HelpOutcome, HelpService
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import Chunk, ChunkRole, Corpus, text_hash
from mathtutor.store.db import make_engine, make_sessionmaker, upgrade
from mathtutor.store.models import HelpRequestRow, ItemHelpState, SessionItem, UsageEntry
from mathtutor.verify.types import CheckRequest, CheckResult, SubmittedAnswer, Verdict

ROOT = Path(__file__).resolve().parents[2]
PROBLEM_ID = "openstax-c1-3.6-221"
TOPIC = "derivatives.chain_rule"
CFG: HelpConfig = load_help_config(DEFAULT_CONFIG_PATH)
CONFUSIONS: dict[str, list[Confusion]] = load_confusions(
    ROOT / "content" / "help" / "confusions.json"
)
URL = "https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule"
START = datetime(2026, 10, 26, 9, 0, tzinfo=UTC)

CORRECT = Verdict(VerdictStatus.CORRECT, VerdictReason.PROVEN, Method.SYMBOLIC)
INCORRECT = Verdict(VerdictStatus.INCORRECT, VerdictReason.COUNTEREXAMPLE, Method.REFUTATION)
WRONG_ANSWER = SubmittedAnswer(AnswerKind.EXPRESSION, ["Multiply", 2, "x"], "2x", None)
GOOD_TEXT = "Think about the **chain rule**: the outer function is $u^3$ where $u = 3x^2+1$."


def chunk(
    chunk_id: str, text: str, section: str = "3.6", role: ChunkRole = ChunkRole.RULE
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        section=section,
        section_title="The Chain Rule" if section == "3.6" else "Other",
        url=URL if section == "3.6" else "https://openstax.org/other",
        role=role,
        text=text,
        content_hash=text_hash(text),
        est_tokens=len(text) // 3 + 1,
    )


DEFAULT_CHUNKS = [
    chunk(
        "c1-3.6-rule1",
        "The chain rule: the derivative of a composite function f(g(x)) is "
        "f'(g(x)) g'(x). Differentiate the outer function, then multiply by the inner.",
    ),
    chunk(
        "c1-3.6-ex1",
        "Example: use the chain rule to find the derivative of a power of a "
        "function, $y = (x^2+1)^5$.",
        role=ChunkRole.EXAMPLE,
    ),
    chunk(
        "c1-3.5-exp1",
        "Derivatives of the trigonometric functions follow from limits.",
        section="3.5",
        role=ChunkRole.EXPLANATION,
    ),
    chunk(
        "c1-3.6-key1",
        "Answer: the chain rule derivative of the composite function.",
        role=ChunkRole.ANSWER_KEY,
    ),
]


def output(
    text: str = GOOD_TEXT,
    ids: tuple[str, ...] = ("c1-3.6-rule1",),
    *,
    abstain: bool = False,
    tokens: tuple[int, int] = (2000, 300),
) -> GenerationResult:
    body = json.dumps({"text": text, "source_ids": list(ids), "abstain": abstain})
    return GenerationResult(body, "end_turn", tokens[0], tokens[1], CFG.model, "req_x", 12)


class MonoClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class WallClock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw: float) -> None:
        self.now += timedelta(**kw)


class FakePool:
    """Returns ``verdict`` (or ``verdict(req)``) for every request; records them."""

    def __init__(self, verdict: Verdict | Callable[[CheckRequest], Verdict] = INCORRECT) -> None:
        self.verdict = verdict
        self.requests: list[CheckRequest] = []

    def submit(self, req: CheckRequest) -> CheckResult:
        self.requests.append(req)
        v = self.verdict(req) if callable(self.verdict) else self.verdict
        return CheckResult(v, "t")


class HookGenerator(ScriptedGenerator):
    """A scripted generator that runs ``before(req)`` at the start of each call."""

    def __init__(
        self,
        script: list[GenerationResult | GeneratorError],
        before: Callable[[GenerationRequest], None] | None = None,
    ) -> None:
        super().__init__(script)
        self.before = before

    def generate(self, req: GenerationRequest) -> GenerationResult:
        if self.before is not None:
            self.before(req)
        return super().generate(req)


def _content() -> LoadedContent:
    real = load_bundle(ROOT / "content" / "compiled" / "problems.json")
    problems = [p for p in real.bundle.problems if p.id == PROBLEM_ID]
    return dataclasses.replace(real, bundle=real.bundle.model_copy(update={"problems": problems}))


CONTENT = _content()


@dataclass
class Kit:
    svc: HelpService
    practice: PracticeService
    sessions: sessionmaker[Session]
    generator: HookGenerator
    ledger: Ledger
    clock: MonoClock
    wall: WallClock
    grade_pool: FakePool
    guard_pool: FakePool
    user: int
    session_id: int
    item: ItemView

    def help(
        self,
        help_type: HelpType = "hint",
        confusion: str | None = None,
        rid: uuid.UUID | None = None,
        revision: int | None = None,
        user: int | None = None,
    ) -> HelpOutcome:
        req = HelpIn(
            help_request_id=rid or uuid.uuid4(),
            session_item_id=self.item.session_item_id,
            item_revision=self.item.revision if revision is None else revision,
            help_type=help_type,
            confusion=confusion,
        )
        return self.svc.request_help(self.user if user is None else user, req)

    def submit_wrong(self) -> None:
        self.practice.submit_answer(
            self.user,
            self.session_id,
            uuid.uuid4(),
            self.item.session_item_id,
            self.item.revision,
            WRONG_ANSWER,
        )
        self.refresh()

    def refresh(self) -> None:
        view = self.practice.current_item(self.user, self.session_id)
        assert isinstance(view, ItemView)
        self.item = view

    def row(self, rid: uuid.UUID | str) -> HelpRequestRow:
        with self.sessions() as db:
            row = db.scalar(select(HelpRequestRow).where(HelpRequestRow.request_id == str(rid)))
            assert row is not None
            return row

    def rows(self) -> list[HelpRequestRow]:
        with self.sessions() as db:
            return list(db.scalars(select(HelpRequestRow).order_by(HelpRequestRow.id)))

    def state(self) -> ItemHelpState | None:
        with self.sessions() as db:
            return db.get(ItemHelpState, self.item.session_item_id)

    def db_item(self) -> SessionItem:
        with self.sessions() as db:
            item = db.get(SessionItem, self.item.session_item_id)
            assert item is not None
            return item

    def usage(self) -> list[UsageEntry]:
        with self.sessions() as db:
            return list(db.scalars(select(UsageEntry).order_by(UsageEntry.id)))


def make_kit(
    tmp_path: Path,
    script: list[GenerationResult | GeneratorError] | None = None,
    *,
    chunks: list[Chunk] | None = None,
    guard_verdict: Verdict | Callable[[CheckRequest], Verdict] = INCORRECT,
    cfg: HelpConfig = CFG,
) -> Kit:
    url = f"sqlite:///{(tmp_path / 'help.db').as_posix()}"
    upgrade(url)
    sessions = make_sessionmaker(make_engine(url))
    clock, wall = MonoClock(), WallClock()
    grade_pool, guard_pool = FakePool(INCORRECT), FakePool(guard_verdict)
    corpus_chunks = DEFAULT_CHUNKS if chunks is None else chunks
    corpus = Corpus({c.chunk_id: c for c in corpus_chunks}, "test-corpus-hash", "test")
    generator = HookGenerator(list(script or []))
    pipeline = HelpPipeline(
        cfg,
        corpus,
        Bm25Index.build(corpus, cfg.retrieval),
        generator,
        LeakGuard(guard_pool, cfg.guard, clock),
        clock,
    )
    ledger = Ledger(sessions, cfg, wall)
    svc = HelpService(
        sessions,
        cfg,
        ledger,
        pipeline,
        FakePool(INCORRECT),
        CONFUSIONS,
        clock=clock,
        now=wall,
    )
    practice = PracticeService(sessions, CONTENT, grade_pool, wall)
    user = AuthService(sessions, wall).register("student", "password-123").user_id
    session_id = practice.start_session(user, [TOPIC])
    view = practice.current_item(user, session_id)
    assert isinstance(view, ItemView)
    return Kit(
        svc,
        practice,
        sessions,
        generator,
        ledger,
        clock,
        wall,
        grade_pool,
        guard_pool,
        user,
        session_id,
        view,
    )
