from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import ValidationError
from support.mathjson import meta, mj

from mathtutor.content.schema import ContentBundle, Problem

VALID: dict[str, Any] = {
    "id": "openstax-c1-3.6-221",
    "topic": "derivatives.chain_rule",
    "difficulty": 2,
    "source": {
        "book": "OpenStax Calculus Volume 1",
        "section": "3.6",
        "exercise": 221,
        "url": "https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule",
        "license": "CC BY-NC-SA 4.0",
    },
    "statement": "Find $\\frac{dy}{dx}$ for $y = \\sin(3x^2)$.",
    "answer": {
        "kind": "expression",
        "latex": "6x\\cos(3x^2)",
        "mathjson": mj("six_x_cos"),
        "variable": "x",
        "domain": {"intervals": [["-inf", "inf", "open", "open"]], "exclude": []},
        "strict_domain": False,
    },
    "misconceptions": [],
    "review": {"status": "human_verified", "reviewer": "tg", "date": "2026-10-20", "notes": ""},
}


def deep_set(d: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    out = copy.deepcopy(d)
    cur = out
    *head, last = path.split(".")
    for key in head:
        cur = cur[key]
    cur[last] = value
    return out


def deep_del(d: dict[str, Any], path: str) -> dict[str, Any]:
    out = copy.deepcopy(d)
    cur = out
    *head, last = path.split(".")
    for key in head:
        cur = cur[key]
    del cur[last]
    return out


def numeric(precision: Any) -> dict[str, Any]:
    ans: dict[str, Any] = {"kind": "numeric", "latex": "0.785", "mathjson": mj("dec_0785")}
    if precision is not None:
        ans["precision"] = precision
    return deep_set(VALID, "answer", ans)


def choice(correct: str) -> dict[str, Any]:
    ch = [{"id": i, "latex": "x", "mathjson": "x"} for i in "abc"]
    ans = {"kind": "choice", "choices": ch, "correct": correct}
    return deep_set(VALID, "answer", ans)


def test_valid_problem_parses() -> None:
    assert Problem.model_validate(VALID).answer.kind == "expression"


def test_unknown_field_rejected() -> None:
    bad = deep_set(VALID, "answer.strict_domian", True)
    with pytest.raises(ValidationError) as e:
        Problem.model_validate(bad)
    assert "strict_domian" in str(e.value)


@pytest.mark.parametrize(
    "iv",
    [
        ["1", "0", "open", "open"],
        ["-inf", "0", "closed", "open"],
        ["a", "1", "open", "open"],
        ["0", "1", "open", "half"],
    ],
)
def test_bad_interval_rejected(iv: list[str]) -> None:
    bad = deep_set(VALID, "answer.domain.intervals", [iv])
    with pytest.raises(ValidationError):
        Problem.model_validate(bad)


def test_good_rational_interval_accepted() -> None:
    ok = deep_set(VALID, "answer.domain.intervals", [["-1/2", "3", "closed", "open"]])
    Problem.model_validate(ok)


def test_exclude_outside_domain_rejected() -> None:
    dom = {"intervals": [["0", "1", "open", "open"]], "exclude": ["5"]}
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "answer.domain", dom))


def test_exclude_at_open_endpoint_rejected() -> None:
    dom = {"intervals": [["0", "1", "open", "open"]], "exclude": ["0"]}
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "answer.domain", dom))


def test_exclude_inside_domain_accepted() -> None:
    dom = {"intervals": [["0", "1", "open", "open"]], "exclude": ["1/2"]}
    Problem.model_validate(deep_set(VALID, "answer.domain", dom))


def test_empty_intervals_rejected() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "answer.domain.intervals", []))


def test_domain_defaults_to_all_reals() -> None:
    p = Problem.model_validate(deep_del(VALID, "answer.domain"))
    assert p.answer.kind == "expression"
    assert [list(i) for i in p.answer.domain.intervals] == [["-inf", "inf", "open", "open"]]
    assert p.answer.domain.exclude == []


def test_choice_answer_valid_and_correct_must_be_a_choice_id() -> None:
    Problem.model_validate(choice("b"))
    with pytest.raises(ValidationError):
        Problem.model_validate(choice("z"))


def test_choice_ids_unique_and_count_bounded() -> None:
    dup = choice("a")
    dup["answer"]["choices"][1]["id"] = "a"
    with pytest.raises(ValidationError):
        Problem.model_validate(dup)
    one = choice("a")
    one["answer"]["choices"] = one["answer"]["choices"][:1]
    with pytest.raises(ValidationError):
        Problem.model_validate(one)


def test_choice_id_pattern() -> None:
    bad = choice("a")
    bad["answer"]["choices"][0]["id"] = "A"
    with pytest.raises(ValidationError):
        Problem.model_validate(bad)


def test_numeric_requires_precision() -> None:
    Problem.model_validate(numeric({"decimals": 3}))
    Problem.model_validate(numeric("exact"))
    with pytest.raises(ValidationError):
        Problem.model_validate(numeric(None))


@pytest.mark.parametrize("p", [{"decimals": 11}, {"decimals": -1}, "approx", {"places": 2}])
def test_bad_precision_rejected(p: Any) -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(numeric(p))


def test_precision_forbidden_on_expression() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "answer.precision", {"decimals": 2}))


def test_human_verified_requires_reviewer_and_iso_date() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "review.reviewer", ""))
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "review.date", "20/10/2026"))
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "review.date", ""))


def test_needs_review_allows_empty_reviewer_and_date() -> None:
    ok = deep_set(VALID, "review", {"status": "needs_review"})
    assert Problem.model_validate(ok).review.reviewer == ""


def test_non_openstax_url_rejected() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "source.url", "https://example.com/x"))


def test_wrong_license_rejected() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "source.license", "MIT"))


@pytest.mark.parametrize("d", [0, 6])
def test_difficulty_range(d: int) -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "difficulty", d))


def test_problem_id_pattern() -> None:
    with pytest.raises(ValidationError):
        Problem.model_validate(deep_set(VALID, "id", "Bad_ID"))


def test_models_are_frozen() -> None:
    p = Problem.model_validate(VALID)
    with pytest.raises(ValidationError):
        p.difficulty = 3  # type: ignore[misc]


def test_bundle_parses_and_tool_versions_match_capture() -> None:
    m = meta()
    bundle = {
        "schema_version": 1,
        "tools": {"mathlive": m["mathlive"], "compute_engine": m["compute_engine"]},
        "topics": [
            {
                "topic_id": "derivatives.chain_rule",
                "title": "The chain rule",
                "order": 3,
                "section": "3.6",
            }
        ],
        "problems": [VALID],
    }
    b = ContentBundle.model_validate(bundle)
    assert b.tools.compute_engine == "0.151.0"
    with pytest.raises(ValidationError):
        ContentBundle.model_validate({**bundle, "schema_version": 2})
    with pytest.raises(ValidationError):
        ContentBundle.model_validate({**bundle, "tools": {"mathlive": "1"}})
