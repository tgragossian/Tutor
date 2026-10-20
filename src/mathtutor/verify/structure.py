"""Cheap structural bounds on submitted MathJSON (spec 03); safe to run in the web process."""

from __future__ import annotations

import re

from pydantic import JsonValue

from mathtutor.domain import FormatIssueCode
from mathtutor.verify.types import FormatIssue

MAX_NODES = 200
MAX_DEPTH = 30
MAX_INT_DIGITS = 30
MAX_SIG_DIGITS = 30
MAX_EXPONENT = 30

# 10**30 - 1 needs 100 bits, so anything wider has more than 30 digits.
_MAX_INT_BITS = 100
_DECIMAL = re.compile(r"(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?")


def _too_large(detail: str) -> FormatIssue:
    return FormatIssue(FormatIssueCode.INPUT_TOO_LARGE, detail)


def _unsupported(detail: str) -> FormatIssue:
    return FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, detail)


def _check_int(value: int) -> FormatIssue | None:
    if value.bit_length() > _MAX_INT_BITS or len(str(abs(value))) > MAX_INT_DIGITS:
        return _too_large(f"integer has more than {MAX_INT_DIGITS} digits")
    return None


def _check_num(literal: str) -> FormatIssue | None:
    body = literal[1:] if literal.startswith("-") else literal
    match = _DECIMAL.fullmatch(body)
    if match is None or not (match.group(1) or match.group(2)):
        return _unsupported("not a decimal literal")
    int_part, frac_part, exp = match.group(1), match.group(2) or "", match.group(3)
    if len((int_part + frac_part).lstrip("0")) > MAX_SIG_DIGITS:
        return _too_large(f"decimal has more than {MAX_SIG_DIGITS} significant digits")
    if exp is not None:
        exp_digits = exp.lstrip("+-").lstrip("0")
        if len(exp_digits) > 3 or int(exp_digits or "0") > MAX_EXPONENT:
            return _too_large(f"decimal exponent is beyond +-{MAX_EXPONENT}")
    return None


def check_structure(tree: JsonValue) -> FormatIssue | None:
    """Bound nodes, depth and number sizes with an explicit stack (no recursion).

    A node is each list (operator plus operands, the head string included) and each
    operand atom; depth counts nested lists, the root list being depth 1.
    """
    nodes = 0
    stack: list[tuple[JsonValue, int]] = [(tree, 0)]
    while stack:
        node, depth = stack.pop()
        nodes += 1
        if nodes > MAX_NODES:
            return _too_large(f"more than {MAX_NODES} nodes")
        if isinstance(node, bool) or node is None or isinstance(node, float):
            return _unsupported("unsupported value")
        if isinstance(node, int):
            issue = _check_int(node)
        elif isinstance(node, str):
            issue = None
        elif isinstance(node, dict):
            literal = node.get("num")
            if len(node) != 1 or not isinstance(literal, str):
                return _unsupported("unsupported object")
            issue = _check_num(literal)
        else:
            if not node:
                return _unsupported("empty list")
            if depth + 1 > MAX_DEPTH:
                return _too_large(f"deeper than {MAX_DEPTH} levels")
            head, *operands = node
            if not isinstance(head, str):
                return _unsupported("operator must be a name")
            stack.extend((operand, depth + 1) for operand in operands)
            issue = None
        if issue is not None:
            return issue
    return None
