"""Query builder caps and content."""

import pytest
from support.helpkit import CONTENT

from mathtutor.domain import AnswerKind, VerdictStatus
from mathtutor.help.config import DEFAULT_CONFIG_PATH, load_help_config
from mathtutor.help.context import AttemptLine, HelpContext, assemble_context
from mathtutor.retrieval.query import build_query

PARAMS = load_help_config(DEFAULT_CONFIG_PATH).retrieval
PROBLEM = CONTENT.bundle.problems[0]


def ctx(statement: str, attempts: list[AttemptLine] | None = None) -> HelpContext:
    return HelpContext(
        problem_id="p1",
        topic="chain rule",
        section="3.6",
        statement=statement,
        answer_kind=AnswerKind.EXPRESSION,
        attempts=attempts or [],
        tries_used=len(attempts or []),
        hint_level=1,
        misconception_note=None,
        variable="x",
    )


def test_query_caps() -> None:
    statement = "Differentiate $\\sin(7x)$ with respect to x. " * 10
    query = build_query(ctx(statement), "hint", "é" * 2500, PARAMS)
    assert len(query.encode("utf-8")) <= 1200
    assert query.startswith(statement)


W, C, U = VerdictStatus.INCORRECT, VerdictStatus.CORRECT, VerdictStatus.UNABLE_TO_VERIFY


@pytest.mark.parametrize(
    ("submitted", "latest"),
    [
        ([("a1", W)], "a1"),
        ([("a1", W), ("a2", W)], "a2"),
        ([("a1", W), ("a2", W), ("a3", W)], "a3"),
        ([("a1", W), ("a2", U)], "a1"),  # unable_to_verify is not a wrong answer
        ([("a1", W), ("a2", W), ("a3", U), ("a4", C)], "a2"),
        ([("a1", W), ("a2", W), ("a3", W), ("a4", W), ("a5", W)], "a5"),  # beyond the 3 kept
    ],
)
def test_feedback_queries_the_latest_wrong_attempt(
    submitted: list[tuple[str, VerdictStatus]], latest: str
) -> None:
    """Review C1-R6: built through ``assemble_context`` (oldest first in, newest first out),
    as production and the evaluation build it."""
    attempts = [AttemptLine(f"x^{{{tag}}}", status) for tag, status in submitted]
    context = assemble_context(PROBLEM, attempts, 1, None)
    feedback = build_query(context, "feedback", None, PARAMS)
    included = [tag for tag, _ in submitted if f"x^{{{tag}}}" in feedback]
    assert included == [latest], feedback
    assert "x^{" not in build_query(context, "hint", None, PARAMS)


def test_long_confusion_is_cut_to_500_bytes() -> None:
    query = build_query(ctx("S"), "explain", "w" * 5000, PARAMS)
    assert len(query.encode("utf-8")) <= len("S chain rule ") + 500


def test_caps_come_from_the_config() -> None:
    small = PARAMS.model_copy(update={"query_max_bytes": 40, "question_max_bytes": 5})
    assert len(build_query(ctx("S" * 100), "hint", None, small).encode("utf-8")) == 40
    assert build_query(ctx("S"), "explain", "w" * 50, small) == "S chain rule wwwww"
