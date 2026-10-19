from __future__ import annotations

import pytest
from support.mathjson import latex, mj

from mathtutor.content.schema import ChoiceAnswer, ExpressionAnswer, NumericAnswer
from mathtutor.domain import AnswerKind, FormatIssueCode
from mathtutor.verify.latex_rules import FUNCTION_PARENS_DETAIL
from mathtutor.verify.precheck import decimal_literal, precheck
from mathtutor.verify.types import FormatIssue, SubmittedAnswer

EXPR = ExpressionAnswer(kind="expression", latex="2x", mathjson=["Multiply", 2, "x"])
EXACT = NumericAnswer(kind="numeric", latex="1/2", mathjson=["Divide", 1, 2], precision="exact")
ROUNDED = NumericAnswer(
    kind="numeric", latex="0.5", mathjson={"num": "0.5"}, precision={"decimals": 2}
)
CHOICE = ChoiceAnswer.model_validate(
    {
        "kind": "choice",
        "choices": [
            {"id": "a", "latex": "1", "mathjson": 1},
            {"id": "b", "latex": "2", "mathjson": 2},
        ],
        "correct": "a",
    }
)


def expr_answer(mathjson: object, tex: str) -> SubmittedAnswer:
    return SubmittedAnswer(AnswerKind.EXPRESSION, mathjson, tex, None)  # type: ignore[arg-type]


def num_answer(mathjson: object, tex: str) -> SubmittedAnswer:
    return SubmittedAnswer(AnswerKind.NUMERIC, mathjson, tex, None)  # type: ignore[arg-type]


def test_empty_is_empty() -> None:
    issue = precheck(expr_answer(mj("empty"), latex("empty")), EXPR)
    assert issue is not None and issue.code == "empty"


def test_missing_mathjson_is_empty() -> None:
    issue = precheck(expr_answer(None, "x"), EXPR)
    assert issue is not None and issue.code == "empty"


def test_bare_function_is_unsupported_notation() -> None:
    issue = precheck(expr_answer(["Sin", "x"], r"\sin x"), EXPR)
    assert issue == FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, FUNCTION_PARENS_DETAIL)


def test_parenthesized_function_proceeds() -> None:
    assert precheck(expr_answer(["Sin", "x"], r"\sin(x)"), EXPR) is None


def test_incomplete_wins_over_parens() -> None:
    issue = precheck(expr_answer(["Sin", "x"], r"\sin\placeholder{}"), EXPR)
    assert issue is not None and issue.code == "incomplete"


def test_placeholder_latex_incomplete() -> None:
    issue = precheck(expr_answer(mj("incomplete"), latex("incomplete")), EXPR)
    assert issue is not None and issue.code == "incomplete"


def test_empty_group_incomplete() -> None:
    issue = precheck(expr_answer(mj("typed_pow_empty"), latex("typed_pow_empty")), EXPR)
    assert issue is not None and issue.code == "incomplete"


def test_error_node_incomplete() -> None:
    issue = precheck(expr_answer(mj("typed_frac_empty"), "\frac{1}{x}"), EXPR)
    assert issue is not None and issue.code == "incomplete"


def test_escaped_braces_are_not_an_empty_group() -> None:
    assert precheck(expr_answer(mj("x_plain"), r"\{\}"), EXPR) is None


def test_complete_expression_passes() -> None:
    assert precheck(expr_answer(mj("six_x_cos"), latex("six_x_cos")), EXPR) is None


def test_decimal_when_exact_required() -> None:
    issue = precheck(num_answer({"num": "0.5"}, "0.5"), EXACT)
    assert issue is not None and issue.code == "exact_required"


def test_decimal_inside_tree_is_not_exact_required() -> None:
    assert precheck(num_answer(["Divide", {"num": "0.5"}, 2], "x"), EXACT) is None


def test_decimal_ok_when_rounding_precision() -> None:
    assert precheck(num_answer(mj("dec_250"), latex("dec_250")), ROUNDED) is None


def test_integer_ok_when_exact_required() -> None:
    assert precheck(num_answer(mj("num_3"), "3"), EXACT) is None


def test_choice_skips_expression_prechecks() -> None:
    assert precheck(SubmittedAnswer(AnswerKind.CHOICE, None, "", "b"), CHOICE) is None


def test_choice_without_selection_is_empty() -> None:
    issue = precheck(SubmittedAnswer(AnswerKind.CHOICE, None, "", None), CHOICE)
    assert issue is not None and issue.code == "empty"


def test_kind_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        precheck(expr_answer(mj("x_plain"), "x"), CHOICE)
    with pytest.raises(ValueError):
        precheck(SubmittedAnswer(AnswerKind.CHOICE, None, "", "a"), EXPR)


@pytest.mark.parametrize(
    "tree",
    [
        ["Negate", {"num": "0.5"}],  # how Compute Engine sends -0.5
        ["Delimiter", {"num": "0.5"}],  # (0.5)
        ["Delimiter", ["Negate", {"num": "0.5"}]],  # (-0.5)
    ],
)
def test_top_level_decimal_shapes_when_exact_required(tree: object) -> None:
    issue = precheck(num_answer(tree, "-0.5"), EXACT)
    assert issue is not None and issue.code == "exact_required"


@pytest.mark.parametrize(
    "tree,literal",
    [
        ({"num": "0.5"}, "0.5"),
        ({"num": "-0.5"}, "-0.5"),
        (["Negate", {"num": "0.583"}], "-0.583"),
        (["Delimiter", {"num": "3.14"}], "3.14"),
        (["Negate", ["Delimiter", {"num": "0.5"}]], "-0.5"),
        (["Negate", ["Negate", {"num": "0.5"}]], None),
        (["Negate", {"num": "-0.5"}], None),
        (["Delimiter", {"num": "0.5"}, 1], None),
        (["Divide", {"num": "0.5"}, 2], None),
        (["Negate", 1], None),
        ({"num": 5}, None),
        (None, None),
    ],
)
def test_decimal_literal(tree: object, literal: str | None) -> None:
    assert decimal_literal(tree) == literal  # type: ignore[arg-type]
