from __future__ import annotations

import pytest
from support.mathjson import mj

from mathtutor.verify.structure import check_structure


def _nested(depth: int) -> object:
    node: object = "x"
    for _ in range(depth):
        node = ["Negate", node]
    return node


@pytest.mark.parametrize("key", ["x_plain", "six_x_cos", "rational_fn", "huge_pow", "dec_250"])
def test_captured_shapes_pass_structure(key: str) -> None:
    # huge_pow is a cost issue for the worker (task 3), not a structural one.
    assert check_structure(mj(key)) is None


def test_long_int_too_large() -> None:
    issue = check_structure(mj("long_int"))
    assert issue is not None and issue.code == "input_too_large"


def test_int_digit_limits() -> None:
    assert check_structure(10**30 - 1) is None
    issue = check_structure(10**30)
    assert issue is not None and issue.code == "input_too_large"
    issue = check_structure(-(10**200))
    assert issue is not None and issue.code == "input_too_large"


def test_201_nodes_too_large() -> None:
    issue = check_structure(["Add", *["x"] * 200])
    assert issue is not None and issue.code == "input_too_large"


def test_200_nodes_ok() -> None:
    assert check_structure(["Add", *["x"] * 199]) is None


def test_depth_31_too_large() -> None:
    issue = check_structure(_nested(31))
    assert issue is not None and issue.code == "input_too_large"


def test_depth_30_ok() -> None:
    assert check_structure(_nested(30)) is None


def test_very_deep_tree_does_not_recurse() -> None:
    issue = check_structure(_nested(5000))
    assert issue is not None and issue.code == "input_too_large"


def test_num_31_sig_digits() -> None:
    issue = check_structure({"num": "1." + "2" * 30})
    assert issue is not None and issue.code == "input_too_large"


def test_num_30_sig_digits_ok() -> None:
    assert check_structure({"num": "1." + "2" * 29}) is None
    assert check_structure({"num": "0.000" + "2" * 30}) is None  # leading zeros not significant


def test_num_exponent_31() -> None:
    issue = check_structure({"num": "1e31"})
    assert issue is not None and issue.code == "input_too_large"
    issue = check_structure({"num": "1e-31"})
    assert issue is not None and issue.code == "input_too_large"
    assert check_structure({"num": "1e30"}) is None
    assert check_structure({"num": "1E-30"}) is None


def test_num_huge_exponent_digits() -> None:
    issue = check_structure({"num": "1e" + "9" * 5000})
    assert issue is not None and issue.code == "input_too_large"


@pytest.mark.parametrize("literal", ["abc", "", "1.2.3", "0x10", "1e", "--1", "NaN", " 1"])
def test_num_not_a_decimal_literal(literal: str) -> None:
    issue = check_structure({"num": literal})
    assert issue is not None and issue.code == "unsupported_notation"


@pytest.mark.parametrize(
    "node", [{"sym": "x"}, {"num": 1}, {"num": "1", "x": 2}, None, True, 1.5, []]
)
def test_unsupported_json_shapes(node: object) -> None:
    issue = check_structure(node)  # type: ignore[arg-type]
    assert issue is not None and issue.code == "unsupported_notation"
