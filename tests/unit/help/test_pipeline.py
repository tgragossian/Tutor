"""HelpPipeline used directly, with no database or ledger (the evaluation path, ruling R4)."""

from __future__ import annotations

from support.helpkit import CFG, CONTENT, DEFAULT_CHUNKS, FakePool, MonoClock, output

from mathtutor.help.context import assemble_context
from mathtutor.help.generator import GenerationResult, GeneratorError, ScriptedGenerator
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.help.pipeline import HelpPipeline, HelpStatus
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import Corpus

PROBLEM = CONTENT.bundle.problems[0]


def _pipeline(
    script: list[GenerationResult | GeneratorError],
) -> tuple[HelpPipeline, ScriptedGenerator, MonoClock]:
    corpus = Corpus({c.chunk_id: c for c in DEFAULT_CHUNKS}, "h", "e")
    clock = MonoClock()
    gen = ScriptedGenerator(script)
    guard = LeakGuard(FakePool(), CFG.guard, clock)
    index = Bm25Index.build(corpus, CFG.retrieval)
    return HelpPipeline(CFG, corpus, index, gen, guard, clock), gen, clock


def test_pipeline_runs_without_database() -> None:
    pipe, gen, clock = _pipeline([output(ids=("nope",)), output()])
    ctx = assemble_context(PROBLEM, [], 2, None)
    asked: list[int] = []

    def may_call(n: int) -> bool:
        asked.append(n)
        return True

    result = pipe.run(ctx, "hint", None, PROBLEM.answer, clock() + 15, may_call=may_call)
    assert result.status is HelpStatus.DELIVERED and asked == [2]
    assert [c.call_no for c in result.calls] == [1, 2]
    assert [c.outcome for c in result.calls] == ["invalid_citation", "ok"]
    assert result.cited_ids == ["c1-3.6-rule1"] and result.top_section == "3.6"
    assert "c1-3.6-key1" not in result.retrieved_ids
    assert "Level 2" in gen.requests[0].user


def test_pipeline_unexpected_error_is_unavailable() -> None:
    pipe, _gen, clock = _pipeline([])  # an exhausted script raises RuntimeError
    ctx = assemble_context(PROBLEM, [], 1, None)
    result = pipe.run(ctx, "hint", None, PROBLEM.answer, clock() + 15)
    assert result.status is HelpStatus.UNAVAILABLE and result.reason == "internal_error"
