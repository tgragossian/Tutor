"""The judge is blind to model identity and sees responses in a recorded, seeded random order."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from support.evalkit import PROBLEMS, make_case, make_env
from support.helpkit import CORRECT, DEFAULT_CHUNKS, ROOT, FakePool, output

from mathtutor.help.eval.judge import (
    JUDGE_MODEL,
    JudgeItem,
    build_judge_prompt,
    judge_case,
    judge_items,
    load_rubric,
)
from mathtutor.help.eval.run import CaseRecord, RawOutput, run_case
from mathtutor.help.generator import GenerationResult, ScriptedGenerator

RUBRIC = load_rubric(ROOT / "evals" / "help" / "rubric" / "v1.md")
MODELS = ("claude-haiku-5-5", "claude-sonnet-5-5")


def _items(n: int = 6) -> list[JudgeItem]:
    return [
        JudgeItem(f"{MODELS[i % 2]}#{i}", f"Hint number {i}: look at $u$.", ["c1-3.6-rule1"])
        for i in range(n)
    ]


def _prompt(seed: str, items: list[JudgeItem] | None = None):  # noqa: ANN202
    case = make_case()
    return build_judge_prompt(
        case, PROBLEMS[case.problem_id], None, items or _items(), DEFAULT_CHUNKS[:1], RUBRIC, seed
    )


def test_judge_blind() -> None:
    prompt = _prompt("seed-1")
    text = (prompt.system + prompt.user).lower()
    for marker in ("haiku", "sonnet", "claude", "opus", "#0", "#1"):
        assert marker not in text
    # The order is a permutation of the items, recorded, and reproducible from the seed.
    assert sorted(prompt.order) == sorted(i.key for i in _items())
    assert _prompt("seed-1").order == prompt.order
    orders = {tuple(_prompt(f"seed-{s}").order) for s in range(20)}
    assert len(orders) > 1  # the seed really shuffles
    # The judge gets the authoritative answer and the cited passage text (offline only).
    assert "18x(3x^2+1)^2" in prompt.user and DEFAULT_CHUNKS[0].text[:40] in prompt.user


def _judge_reply(order: list[str], leak: str = "none") -> GenerationResult:
    scores = [
        {
            "response": i + 1,
            "leak": leak,
            "addresses_error": True,
            "endorses_wrong": False,
            "citations_supported": True,
            "math_error": False,
            "useful": True,
            "rationale": "Names the missing inner derivative.",
        }
        for i in range(len(order))
    ]
    body = json.dumps({"scores": scores})
    return GenerationResult(body, "end_turn", 3000, 400, JUDGE_MODEL, None, 10)


def test_judge_case_maps_scores_back_to_items() -> None:
    env = make_env()
    case = make_case()
    records = [
        run_case(case, ScriptedGenerator([output(ids=("nope",)), output()]), m, env) for m in MODELS
    ]
    items = judge_items(records)
    assert len(items) == 4  # both raw outputs of both models parse as help
    gen = ScriptedGenerator([_judge_reply([i.key for i in items])])
    judgment = judge_case(case, records, env, gen, RUBRIC, seed="s")
    assert judgment.status == "ok" and set(judgment.scores) == {i.key for i in items}
    assert gen.requests[0].model == JUDGE_MODEL and judgment.seed == "s:" + case.case_id
    assert judgment.usage == (3000, 400)
    for model in MODELS:
        assert model not in gen.requests[0].user and model not in gen.requests[0].system


def test_judge_invalid_reply_is_flagged_not_guessed() -> None:
    env = make_env()
    case = make_case()
    records = [run_case(case, ScriptedGenerator([output()]), MODELS[0], env)]
    bad = GenerationResult('{"scores": []}', "end_turn", 10, 10, JUDGE_MODEL, None, 1)
    judgment = judge_case(case, records, env, ScriptedGenerator([bad]), RUBRIC, seed="s")
    assert judgment.status == "invalid" and judgment.scores == {}


def test_nothing_to_judge_makes_no_call() -> None:
    env = make_env(retrieval=False)
    case = make_case()
    records = [run_case(case, ScriptedGenerator([]), MODELS[0], env)]
    gen = ScriptedGenerator([])
    judgment = judge_case(case, records, env, gen, RUBRIC, seed="s")
    assert judgment.status == "no_items" and gen.requests == []


@pytest.mark.parametrize("help_type", ["hint", "feedback"])
def test_uncited_baseline_reaches_blind_judge(help_type: str) -> None:
    env, case = make_env(retrieval=False), make_case(help_type=help_type)
    rec = run_case(case, ScriptedGenerator([output(ids=())]), MODELS[0], env)
    rec = CaseRecord.from_json(rec.to_json())
    assert rec.status == "delivered" and rec.no_passages
    items = judge_items([rec])
    assert len(items) == 1 and items[0].cited_ids == []
    gen = ScriptedGenerator([_judge_reply([items[0].key])])
    result = judge_case(case, [rec], env, gen, RUBRIC, seed="baseline")
    assert result.status == "ok" and result.scores[items[0].key].useful
    assert "Cited passages: (none)" in gen.requests[0].user
    assert all(model not in gen.requests[0].user for model in MODELS)


def test_production_classifying_hint_still_reaches_judge() -> None:
    payload = json.loads(output().text)
    payload["mistake_type"] = "rule_misapplied"
    rec = run_case(
        make_case(),
        ScriptedGenerator([replace(output(), text=json.dumps(payload))]),
        MODELS[0],
        make_env(),
    )
    assert rec.status == "delivered" and rec.mistake_type == "rule_misapplied"
    assert len(judge_items([rec])) == 1 and not rec.no_passages


def test_mode_does_not_relax_production_citations_or_baseline_schema() -> None:
    rec = run_case(
        make_case(), ScriptedGenerator([output(ids=())]), MODELS[0], make_env(retrieval=False)
    )
    assert judge_items([rec])
    assert judge_items([replace(rec, no_passages=False)]) == []
    for text in ("not JSON", output().text, '{"text":"x","source_ids":[],"abstain":true}'):
        assert judge_items([replace(rec, raws=[RawOutput(1, text, "end_turn", "ok")])]) == []


def test_blocked_baseline_raw_output_is_still_judged() -> None:
    env = make_env(retrieval=False, guard=FakePool(CORRECT))
    rec = run_case(
        make_case(), ScriptedGenerator([output(text="$2x$", ids=())] * 2), MODELS[0], env
    )
    assert rec.status != "delivered"
    assert all(raw.outcome.startswith("invalid_guard_") for raw in rec.raws)
    assert len(judge_items([rec])) == 2
