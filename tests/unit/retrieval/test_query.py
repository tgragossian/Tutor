"""Query builder caps and content."""

from mathtutor.domain import AnswerKind, VerdictStatus
from mathtutor.help.config import DEFAULT_CONFIG_PATH, load_help_config
from mathtutor.help.context import AttemptLine, HelpContext
from mathtutor.retrieval.query import build_query

PARAMS = load_help_config(DEFAULT_CONFIG_PATH).retrieval


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


def test_feedback_includes_last_wrong_attempt() -> None:
    attempts = [
        AttemptLine("cos(7x)", VerdictStatus.INCORRECT),
        AttemptLine("7cos(7x)", VerdictStatus.CORRECT),
        AttemptLine("7sin(7x)", VerdictStatus.INCORRECT),
    ]
    feedback = build_query(ctx("Differentiate", attempts), "feedback", None, PARAMS)
    assert "7sin(7x)" in feedback
    assert "7cos" not in feedback
    assert "7sin(7x)" not in build_query(ctx("Differentiate", attempts), "hint", None, PARAMS)


def test_long_confusion_is_cut_to_500_bytes() -> None:
    query = build_query(ctx("S"), "explain", "w" * 5000, PARAMS)
    assert len(query.encode("utf-8")) <= len("S chain rule ") + 500


def test_caps_come_from_the_config() -> None:
    small = PARAMS.model_copy(update={"query_max_bytes": 40, "question_max_bytes": 5})
    assert len(build_query(ctx("S" * 100), "hint", None, small).encode("utf-8")) == 40
    assert build_query(ctx("S"), "explain", "w" * 50, small) == "S chain rule wwwww"
