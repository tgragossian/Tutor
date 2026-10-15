"""Format pre-checks on a submitted answer, before any translation or cost estimate."""

from __future__ import annotations

import re

from pydantic import JsonValue

from mathtutor.content.schema import Answer, NumericAnswer
from mathtutor.domain import AnswerKind, FormatIssueCode
from mathtutor.verify.types import FormatIssue, SubmittedAnswer

_EMPTY_GROUP = re.compile(r"\{\s*\}")
_ESCAPED_BRACE = re.compile(r"\\[{}]")


def _has_error_node(tree: JsonValue) -> bool:
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            if node and node[0] == "Error":
                return True
            stack.extend(node)
    return False


def _is_empty(mathjson: JsonValue | None) -> bool:
    return mathjson is None or mathjson == "Nothing" or mathjson == ["Sequence"]


def _is_incomplete(answer: SubmittedAnswer, mathjson: JsonValue) -> bool:
    tex = _ESCAPED_BRACE.sub("", answer.latex)
    return "\\placeholder" in tex or bool(_EMPTY_GROUP.search(tex)) or _has_error_node(mathjson)


def precheck(answer: SubmittedAnswer, spec: Answer) -> FormatIssue | None:
    """Return the format issue to show the student, or None to proceed.

    Raises ValueError when the answer kind does not match the spec kind (a client bug).
    """
    if answer.kind != spec.kind:
        raise ValueError(f"answer kind {answer.kind!s} does not match problem kind {spec.kind}")
    if answer.kind == AnswerKind.CHOICE:
        return FormatIssue(FormatIssueCode.EMPTY) if answer.choice_id is None else None
    mathjson = answer.mathjson
    if mathjson is None or _is_empty(mathjson):
        return FormatIssue(FormatIssueCode.EMPTY)
    if _is_incomplete(answer, mathjson):
        return FormatIssue(FormatIssueCode.INCOMPLETE)
    if (
        isinstance(spec, NumericAnswer)
        and spec.precision == "exact"
        and isinstance(mathjson, dict)
        and "num" in mathjson
    ):
        return FormatIssue(FormatIssueCode.EXACT_REQUIRED)
    return None
