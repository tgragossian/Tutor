"""The leak guard against the real SymPy checker in a guard-sized verifier pool (C1 Task 3)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import Answer, ExpressionAnswer, NumericAnswer
from mathtutor.help.config import load_help_config
from mathtutor.help.leak_guard import LeakGuard, LeakStatus
from mathtutor.verify.pool import VerifierPool

ROOT = Path(__file__).resolve().parents[2]
PROBLEMS = {
    p.id: p for p in load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
}
LIMITS = load_help_config(ROOT / "src" / "mathtutor" / "help" / "help_config.json").guard


@pytest.fixture(scope="module")
def guard() -> Iterator[LeakGuard]:
    pool = VerifierPool(
        size=1,
        deadline_s=LIMITS.pool_deadline_s,
        queue_max=LIMITS.queue_max,
        queue_wait_s=LIMITS.queue_wait_s,
    )
    try:
        yield LeakGuard(pool, LIMITS, time.monotonic)
    finally:
        pool.close()


def _answer(problem_id: str) -> Answer:
    return PROBLEMS[problem_id].answer


@pytest.mark.parametrize(
    ("problem_id", "text", "decision", "status"),
    [
        ("adapted-c1-3.5-x2cosx", r"Try $x(2\cos x - x\sin x)$.", "block", LeakStatus.LEAK),
        ("adapted-c1-3.5-x2cosx", r"Is it $2x\cos x$?", "pass", LeakStatus.NO_MATCH),
        ("openstax-c1-3.6-215", r"So $126(7x-4)^2$.", "block", LeakStatus.LEAK),
        ("openstax-c1-3.6-215", r"So $18\cdot 7(7x-4)^2$.", "block", LeakStatus.LEAK),
        ("openstax-c1-3.6-215", r"Not $18(7x-4)^2$.", "pass", LeakStatus.NO_MATCH),
        ("openstax-c1-3.6-215", r"First $18u^2$.", "pass", LeakStatus.NO_MATCH),
    ],
)
def test_guard_with_real_checker(
    guard: LeakGuard, problem_id: str, text: str, decision: str, status: LeakStatus
) -> None:
    result = guard.check(text, _answer(problem_id), time.monotonic() + 10.0)
    assert result.decision == decision, result
    assert result.counts[status] == 1, result


def test_foreign_candidate_is_counted_separately(guard: LeakGuard) -> None:
    result = guard.check(r"First $18u^2$.", _answer("openstax-c1-3.6-215"), time.monotonic() + 10)
    assert (result.reason, result.foreign) == ("checked", 1)


def test_restated_problem_passes(guard: LeakGuard) -> None:
    text = r"Since $y = x^2\cos x$, use the product rule."
    result = guard.check(text, _answer("adapted-c1-3.5-x2cosx"), time.monotonic() + 10.0)
    assert (result.decision, result.foreign) == ("pass", 1), result
    assert result.counts[LeakStatus.NO_MATCH] == 2, result


TWO_X = ExpressionAnswer(kind="expression", latex="2x", mathjson=["Multiply", 2, "x"])
TWELVE = NumericAnswer(kind="numeric", latex="12", mathjson=12, precision="exact")


@pytest.mark.parametrize(
    ("answer", "text", "decision"),
    [
        (TWO_X, "Then $2t$.", "block"),
        (TWO_X, "So $2x + C$.", "block"),
        (TWO_X, "Not $2x + 1$ or $3u$.", "pass"),
        (TWELVE, "The answer is 12.", "block"),
        (TWELVE, "It equals -12", "block"),
        (TWELVE, "Not 13, and not 24/3.", "pass"),
    ],
)
def test_round_1_paths_with_real_checker(
    guard: LeakGuard, answer: Answer, text: str, decision: str
) -> None:
    result = guard.check(text, answer, time.monotonic() + 10.0)
    assert result.decision == decision, result


@pytest.mark.parametrize(
    ("answer", "text", "decision"),
    [
        ("openstax-c1-3.6-253", "It is 200/343", "block"),
        ("openstax-c1-3.6-253", "It is -200 / 343", "block"),
        ("openstax-c1-3.6-253", "Use 7 and 3 first.", "pass"),
        ("openstax-c1-3.3-145", "So 12 / 121", "block"),
        ("openstax-c1-3.6-215", "First $18u^2$.", "pass"),
        (TWO_X, "So $2t + C$.", "block"),
        (TWO_X, "The answer is 2x.", "block"),
        (TWO_X, "Answer: **2x**", "block"),
        (TWO_X, "multiply by 3x", "pass"),
    ],
)
def test_round_3_paths_with_real_checker(
    guard: LeakGuard, answer: Answer | str, text: str, decision: str
) -> None:
    spec = _answer(answer) if isinstance(answer, str) else answer
    result = guard.check(text, spec, time.monotonic() + 10.0)
    assert result.decision == decision, result


@pytest.mark.parametrize(
    ("answer", "text", "decision"),
    [
        (TWELVE, "x = 12cm", "block"),
        (TWELVE, "The total = 12 m.", "block"),
        (TWELVE, "So $12 m$.", "block"),
        (TWELVE, "So $12m$.", "block"),
        (TWELVE, "Take the 2nd derivative, then the 3rd.", "no_detected_math"),
        ("openstax-c1-3.6-253", r"So $-\frac{200}{343} m$.", "block"),
        ("openstax-c1-3.6-253", "It is 200/(343)", "block"),
        ("openstax-c1-3.6-253", "So $7 m$ and $3 m$.", "pass"),
        ("openstax-c1-3.3-145", "So 12 /\n121.", "block"),
    ],
)
def test_round_4_paths_with_real_checker(
    guard: LeakGuard, answer: Answer | str, text: str, decision: str
) -> None:
    spec = _answer(answer) if isinstance(answer, str) else answer
    result = guard.check(text, spec, time.monotonic() + 10.0)
    assert result.decision == decision, result


# Review C1-R2: the answer plus foreign terms that cancel (or vanish) must not pass. Each
# foreign atom is substituted (variable, 0, each alone) and every variant is really checked.
@pytest.mark.parametrize(
    "suffix",
    [
        "f(x)-f(x)",
        r"\theta-\theta",
        "y'-y'",
        "x_1-x_1",
        r"0\cdot g(x)",
        r"\alpha\cdot(x-x)",
        r"f(x)-f(2x)",
    ],
)
def test_answer_plus_canceling_foreign_terms_is_blocked(guard: LeakGuard, suffix: str) -> None:
    answer = _answer("openstax-c1-3.6-221")
    result = guard.check(f"${answer.latex}+{suffix}$", answer, time.monotonic() + 10.0)
    assert result.decision == "block", result


@pytest.mark.parametrize("text", [r"So $12+\theta-\theta$.", r"So $12 + 0\cdot f(x)$."])
def test_numeric_answer_plus_canceling_foreign_terms_is_blocked(
    guard: LeakGuard, text: str
) -> None:
    result = guard.check(text, TWELVE, time.monotonic() + 10.0)
    assert result.decision == "block", result


@pytest.mark.parametrize(
    "text",
    [
        r"Write $y = u^3$ where $u = 3x^2+1$; then $\frac{dy}{dx} = 3u^2 \cdot u'$.",
        r"The chain rule gives $f'(g(x))\,g'(x)$.",
        r"Differentiate the inside: $\frac{d}{dx}(3x^2+1)$.",
    ],
)
def test_safe_derivative_notation_passes(guard: LeakGuard, text: str) -> None:
    result = guard.check(text, _answer("openstax-c1-3.6-221"), time.monotonic() + 10.0)
    assert result.decision == "pass", result
