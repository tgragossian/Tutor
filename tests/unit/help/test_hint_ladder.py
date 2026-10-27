"""The hint ladder follows the mistake (ruling R35, Thomas 2026-10-27): prompts, reply shape,
evaluation cases and the runner. Service behavior is in ``test_service.py``."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from support.evalkit import make_case, make_env
from support.helpkit import CFG, CONTENT, GOOD_TEXT

from mathtutor.domain import VerdictStatus
from mathtutor.help.context import AttemptLine, assemble_context
from mathtutor.help.eval.report import mistake_agreement
from mathtutor.help.eval.run import run_case
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    HINT_CHOICE_SCHEMA,
    FixedHintGenerator,
    GenerationRequest,
    GenerationResult,
    ScriptedGenerator,
)
from mathtutor.help.prompts import LEVEL_RULES, build_prompt

PROBLEM = CONTENT.bundle.problems[0]
HAIKU = "claude-haiku-5-5"
WRONG = [AttemptLine("a", VerdictStatus.INCORRECT), AttemptLine("b", VerdictStatus.INCORRECT)]


def _ctx(level: int, attempts: list[AttemptLine] | None = None):  # type: ignore[no-untyped-def]
    return assemble_context(PROBLEM, attempts or [], level, None)


def test_four_levels_and_level_0_prompt() -> None:
    assert sorted(LEVEL_RULES) == [0, 1, 2, 3]
    system, user = build_prompt(_ctx(0), "hint", [], None, False)
    assert "Level 0 hint: how to start" in user
    assert "Level 0" in system and "Level 3" in system


def test_choice_prompt_offers_the_level_and_level_1() -> None:
    _, user = build_prompt(_ctx(3, WRONG), "hint", [], None, False, hint_choice=True)
    assert "Level 3" in user and LEVEL_RULES[3] in user and LEVEL_RULES[1] in user
    assert 'Set `mistake` to "same"' in user and 'Set `mistake` to "new"' in user


@pytest.mark.parametrize(("level", "help_type"), [(1, "hint"), (0, "hint"), (3, "feedback")])
def test_choice_needs_a_level_2_or_3_hint(level: int, help_type: str) -> None:
    with pytest.raises(ValueError):
        build_prompt(_ctx(level, WRONG), help_type, [], None, False, hint_choice=True)  # type: ignore[arg-type]


def test_choice_schema_is_the_help_schema_plus_mistake() -> None:
    assert HINT_CHOICE_SCHEMA["required"] == [*HELP_OUTPUT_SCHEMA["required"], "mistake"]
    assert HINT_CHOICE_SCHEMA["properties"]["mistake"]["enum"] == ["same", "new"]
    assert "mistake" not in HELP_OUTPUT_SCHEMA["properties"]


def test_fixed_test_generator_answers_a_choice() -> None:
    req = GenerationRequest(HAIKU, "low", "s", '<passage id="c1">', HINT_CHOICE_SCHEMA, 10, 1.0)
    reply = json.loads(FixedHintGenerator().generate(req).text or "")
    assert reply["mistake"] == "same"


def test_case_rules() -> None:
    make_case(attempts=[], hint_level=0, tags=["ordinary"])
    with pytest.raises(ValidationError, match="level 0"):
        make_case(attempts=[], hint_level=1, tags=["ordinary"])
    with pytest.raises(ValidationError, match="level 0"):
        make_case(hint_level=0)  # has an attempt
    with pytest.raises(ValidationError, match="two attempts"):
        make_case(hint_choice=True, expect_mistake="same", hint_level=3)  # one attempt
    with pytest.raises(ValidationError, match="expect_mistake"):
        make_case(attempts=["a", "b"], hint_choice=True, hint_level=3)
    with pytest.raises(ValidationError, match="expect_mistake"):
        make_case(expect_mistake="new")
    make_case(attempts=["a", "b"], hint_choice=True, expect_mistake="new", hint_level=3)


def _reply(mistake: str) -> GenerationResult:
    body = {"text": GOOD_TEXT, "source_ids": ["c1-3.6-rule1"], "abstain": False, "mistake": mistake}
    return GenerationResult(json.dumps(body), "end_turn", 2000, 300, HAIKU, None, 1)


def test_runner_sends_the_choice_and_records_the_call() -> None:
    case = make_case(
        attempts=["3(3x^2+1)^2", "3(3x^2+1)^2\\cdot 2"],
        hint_choice=True,
        expect_mistake="same",
        hint_level=3,
    )
    gen = ScriptedGenerator([_reply("new")])
    record = run_case(case, gen, HAIKU, make_env())
    assert gen.requests[0].schema == HINT_CHOICE_SCHEMA
    assert (record.hint_choice, record.expect_mistake, record.mistake) == (True, "same", "new")
    assert mistake_agreement([record]) == f"{HAIKU} 0/1"


def test_plain_case_uses_the_help_schema() -> None:
    gen = ScriptedGenerator([_reply("same")])  # an extra field fails the strict help shape
    record = run_case(
        make_case(), gen, HAIKU, make_env(cfg=CFG.model_copy(update={"max_calls": 1}))
    )
    assert gen.requests[0].schema == HELP_OUTPUT_SCHEMA and record.mistake is None
    assert mistake_agreement([record]) == "none delivered"
