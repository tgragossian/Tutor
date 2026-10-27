"""HelpPipeline used directly, with no database or ledger (the evaluation path, ruling R4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.helpkit import CFG, CONTENT, DEFAULT_CHUNKS, FakePool, MonoClock, chunk, output

from mathtutor.help.config import DEFAULT_CONFIG_PATH, HelpConfig, load_help_config
from mathtutor.help.context import assemble_context
from mathtutor.help.generator import GenerationResult, GeneratorError, ScriptedGenerator
from mathtutor.help.leak_guard import LeakGuard
from mathtutor.help.pipeline import HelpPipeline, HelpStatus
from mathtutor.retrieval.bm25 import Bm25Index
from mathtutor.retrieval.corpus import Chunk, Corpus

PROBLEM = CONTENT.bundle.problems[0]


def _pipeline(
    script: list[GenerationResult | GeneratorError],
    chunks: list[Chunk] | None = None,
    cfg: HelpConfig = CFG,
) -> tuple[HelpPipeline, ScriptedGenerator, MonoClock]:
    corpus = Corpus({c.chunk_id: c for c in chunks or DEFAULT_CHUNKS}, "h", "e")
    clock = MonoClock()
    gen = ScriptedGenerator(script)
    guard = LeakGuard(FakePool(), cfg.guard, clock)
    index = Bm25Index.build(corpus, cfg.retrieval)
    return HelpPipeline(cfg, corpus, index, gen, guard, clock), gen, clock


def _retrieved(answer_latex: str, texts: dict[str, str]) -> list[str]:
    chunks = [chunk(cid, f"The chain rule derivative. {t}") for cid, t in texts.items()]
    pipe, _gen, _clock = _pipeline([], chunks)
    answer = PROBLEM.answer.model_copy(update={"latex": answer_latex})
    ctx = assemble_context(PROBLEM, [], 1, None)
    return sorted(c.chunk_id for c in pipe.retrieve(ctx, "hint", None, answer))


def test_short_answer_drops_only_exact_math_spans() -> None:
    texts = {
        "c-plain": "Multiply by 2 and then by 12.",
        "c-power": "Here $x^2$ appears and $2x$ too.",
        "c-alone": "The value is $ 2 $ here.",
        "c-display": "Display $$2$$ form.",
    }
    assert _retrieved("2", texts) == ["c-plain", "c-power"]


def test_short_answer_never_empties_retrieval_by_substring() -> None:
    assert _retrieved("2", {"c-a": "Step 2 of 12.", "c-b": "Use 2 rules."}) == ["c-a", "c-b"]


def test_long_answer_still_drops_by_stripped_substring() -> None:
    texts = {"c-leak": "so it is 18 x(3x^2 + 1)^2 overall", "c-ok": "multiply by 6x"}
    assert _retrieved("18x(3x^2+1)^2", texts) == ["c-ok"]


def test_max_calls_is_clamped_to_two() -> None:
    loose = CFG.model_copy(update={"max_calls": 5})  # model_copy skips validation
    bad = output(ids=("nope",))
    pipe, gen, clock = _pipeline([bad, bad, bad, bad], cfg=loose)
    ctx = assemble_context(PROBLEM, [], 1, None)
    result = pipe.run(ctx, "hint", None, PROBLEM.answer, clock() + 15)
    assert result.status is HelpStatus.FALLBACK and len(gen.requests) == 2


@pytest.mark.parametrize("value", [0, 3])
def test_config_rejects_max_calls_outside_1_to_2(tmp_path: Path, value: int) -> None:
    data = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    data["max_calls"] = value
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_help_config(path)


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
