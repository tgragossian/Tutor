"""The judge is blind to model identity and sees responses in a recorded, seeded random order."""

from __future__ import annotations

import json

from support.evalkit import PROBLEMS, make_case, make_env
from support.helpkit import DEFAULT_CHUNKS, ROOT, output

from mathtutor.help.eval.judge import (
    JUDGE_MODEL,
    JudgeItem,
    build_judge_prompt,
    judge_case,
    judge_items,
    load_rubric,
)
from mathtutor.help.eval.run import run_case
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
