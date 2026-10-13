from __future__ import annotations

import copy
import json
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from mathtutor.web.schemas import ErrorBody, PublicItem, SubmissionRequest

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"
SUBMITS = sorted(EXAMPLES.glob("submit-*.json"))
ITEMS = sorted(EXAMPLES.glob("item-*.json"))


def _load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLES / name).read_text(encoding="utf-8"))
    return data


def test_examples_exist() -> None:
    assert len(SUBMITS) == 3
    assert len(ITEMS) == 2


@pytest.mark.parametrize("path", SUBMITS, ids=lambda p: p.name)
def test_submit_examples_parse(path: Path) -> None:
    SubmissionRequest.model_validate_json(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", ITEMS, ids=lambda p: p.name)
def test_item_examples_parse(path: Path) -> None:
    PublicItem.model_validate_json(path.read_text(encoding="utf-8"))


def _kind_matrix(d: dict[str, Any]) -> dict[str, Any]:
    d["answer"] = {"kind": "choice", "latex": "x", "mathjson": "x"}
    return d


def _uuid_v1(d: dict[str, Any]) -> dict[str, Any]:
    d["submission_id"] = str(uuid.uuid1())
    return d


def _choice_upper(d: dict[str, Any]) -> dict[str, Any]:
    d["answer"] = {"kind": "choice", "choice_id": "B"}
    return d


def _choice_with_mathjson(d: dict[str, Any]) -> dict[str, Any]:
    d["answer"] = {"kind": "choice", "choice_id": "b", "mathjson": "x"}
    return d


def _extra_field(d: dict[str, Any]) -> dict[str, Any]:
    d["extra"] = 1
    return d


def _long_latex(d: dict[str, Any]) -> dict[str, Any]:
    d["answer"]["latex"] = "x" * 2001
    return d


def _bad_item_id(d: dict[str, Any]) -> dict[str, Any]:
    d["session_item_id"] = 0
    return d


def _neg_revision(d: dict[str, Any]) -> dict[str, Any]:
    d["item_revision"] = -1
    return d


def _unknown_kind(d: dict[str, Any]) -> dict[str, Any]:
    d["answer"]["kind"] = "limit"
    return d


@pytest.mark.parametrize(
    "mutate",
    [
        _kind_matrix,
        _uuid_v1,
        _choice_upper,
        _choice_with_mathjson,
        _extra_field,
        _long_latex,
        _bad_item_id,
        _neg_revision,
        _unknown_kind,
    ],
)
def test_invalid_submissions_rejected(mutate: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
    bad = mutate(copy.deepcopy(_load("submit-expression.json")))
    with pytest.raises(ValidationError):
        SubmissionRequest.model_validate(bad)


def test_expression_requires_mathjson() -> None:
    bad = _load("submit-expression.json")
    del bad["answer"]["mathjson"]
    with pytest.raises(ValidationError):
        SubmissionRequest.model_validate(bad)


def test_public_item_has_no_private_fields() -> None:
    private = {"latex", "mathjson", "correct", "misconceptions", "review", "answer"}
    assert not private & set(PublicItem.model_fields)


def test_public_choice_has_no_correctness_or_mathjson() -> None:
    item = PublicItem.model_validate(_load("item-choice.json"))
    assert item.choices is not None
    assert set(type(item.choices[0]).model_fields) == {"id", "label_latex"}


def test_public_item_rejects_extra_field() -> None:
    bad = _load("item-expression.json")
    bad["answer"] = {"latex": "x"}
    with pytest.raises(ValidationError):
        PublicItem.model_validate(bad)


def test_error_body() -> None:
    assert ErrorBody(error="bad", message="m").error == "bad"
