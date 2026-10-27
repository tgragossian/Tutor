"""A hint ladder per mistake type (ruling R35, Thomas 2026-10-27): prompts, reply shape,
evaluation cases and the runner. Service behavior is in ``test_service.py``."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from support.evalkit import make_case, make_env
from support.helpkit import CONTENT, GOOD_TEXT

from mathtutor.help.context import assemble_context
from mathtutor.help.eval.report import mistake_agreement
from mathtutor.help.eval.run import hint_levels, run_case
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    HINT_CHOICE_SCHEMA,
    MISTAKE_TYPES,
    FixedHintGenerator,
    GenerationRequest,
    GenerationResult,
    ScriptedGenerator,
)
from mathtutor.help.prompts import LEVEL_RULES, build_prompt

PROBLEM = CONTENT.bundle.problems[0]
HAIKU = "claude-haiku-5-5"
LEVELS = {"algebra": 3, "wrong_rule": 1, "rule_misapplied": 2, "incomplete": 1}


def _ctx(level: int = 1):  # type: ignore[no-untyped-def]
    return assemble_context(PROBLEM, [], level, None)


def test_four_levels_and_level_0_prompt() -> None:
    assert sorted(LEVEL_RULES) == [0, 1, 2, 3]
    system, user = build_prompt(_ctx(0), "hint", [], None, False)
    assert "Level 0 hint: how to start" in user
    assert "Level 0" in system and "Level 3" in system and "mistake_type" in system


def test_classifying_prompt_lists_every_type_and_used_rules() -> None:
    _, user = build_prompt(_ctx(), "hint", [], None, False, hint_levels=LEVELS)
    for kind, level in LEVELS.items():
        assert f"`{kind}`" in user and f"): Level {level}" in user
    for n in (1, 2, 3):
        assert f"- Level {n}: {LEVEL_RULES[n]}" in user
    assert "Set `mistake_type`" in user


@pytest.mark.parametrize(
    ("levels", "help_type"),
    [
        ({**LEVELS, "algebra": 0}, "hint"),  # level 0 is never offered to a type
        ({k: v for k, v in LEVELS.items() if k != "incomplete"}, "hint"),  # a type missing
        (LEVELS, "feedback"),
    ],
)
def test_classifying_prompt_rejects_bad_levels(levels: dict[str, int], help_type: str) -> None:
    with pytest.raises(ValueError):
        build_prompt(_ctx(), help_type, [], None, False, hint_levels=levels)  # type: ignore[arg-type]


def test_choice_schema_is_the_help_schema_plus_mistake_type() -> None:
    assert HINT_CHOICE_SCHEMA["required"] == [*HELP_OUTPUT_SCHEMA["required"], "mistake_type"]
    assert HINT_CHOICE_SCHEMA["properties"]["mistake_type"]["enum"] == list(MISTAKE_TYPES)
    assert "mistake_type" not in HELP_OUTPUT_SCHEMA["properties"]


def test_fixed_test_generator_answers_a_classifying_hint() -> None:
    req = GenerationRequest(HAIKU, "low", "s", '<passage id="c1">', HINT_CHOICE_SCHEMA, 10, 1.0)
    reply = json.loads(FixedHintGenerator().generate(req).text or "")
    assert reply["mistake_type"] in MISTAKE_TYPES


def test_case_rules() -> None:
    make_case(attempts=[], hint_level=0, tags=["ordinary"])
    with pytest.raises(ValidationError, match="level 0"):
        make_case(attempts=[], hint_level=1, tags=["ordinary"])
    with pytest.raises(ValidationError, match="expect_mistake_type"):
        make_case(expect_mistake_type=None)  # a hint with an attempt needs a label
    with pytest.raises(ValidationError, match="prior_hints"):
        make_case(hint_level=3, expect_mistake_type="algebra", prior_hints={"algebra": 1})
    with pytest.raises(ValidationError, match="mistake types"):
        make_case(hint_level=1, expect_mistake_type="algebra", prior_hints={"typo": 1})
    with pytest.raises(ValidationError, match="expect_mistake_type"):
        make_case(help_type="feedback", expect_mistake_type="algebra")
    make_case(hint_level=3, expect_mistake_type="algebra", prior_hints={"algebra": 2})


def _reply(kind: str) -> GenerationResult:
    body = {
        "text": GOOD_TEXT,
        "source_ids": ["c1-3.6-rule1"],
        "abstain": False,
        "mistake_type": kind,
    }
    return GenerationResult(json.dumps(body), "end_turn", 2000, 300, HAIKU, None, 1)


def test_runner_offers_levels_from_prior_hints_and_records_the_type() -> None:
    case = make_case(
        attempts=["3(3x^2+1)^2"],
        hint_level=3,
        expect_mistake_type="algebra",
        prior_hints={"algebra": 2, "wrong_rule": 1},
    )
    assert hint_levels(case) == {
        "algebra": 3,
        "wrong_rule": 2,
        "rule_misapplied": 1,
        "incomplete": 1,
    }
    gen = ScriptedGenerator([_reply("wrong_rule")])
    record = run_case(case, gen, HAIKU, make_env())
    assert gen.requests[0].schema == HINT_CHOICE_SCHEMA
    assert (record.expect_mistake_type, record.mistake_type) == ("algebra", "wrong_rule")
    assert mistake_agreement([record]) == f"{HAIKU} 0/1"


def test_level_0_and_other_types_do_not_classify() -> None:
    for case in (
        make_case(attempts=[], tags=["ordinary"]),
        make_case(help_type="feedback", tags=["ordinary"]),
    ):
        assert hint_levels(case) is None
        gen = ScriptedGenerator([_reply("algebra")], default_mistake_type=None)
        record = run_case(case, gen, HAIKU, make_env())
        assert gen.requests[0].schema == HELP_OUTPUT_SCHEMA and record.mistake_type is None
    assert mistake_agreement([record]) == "none delivered"
