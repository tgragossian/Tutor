from __future__ import annotations

from decimal import Decimal

import pytest
from sympy import Rational

from mathtutor.verify.numeric import round_matches


@pytest.mark.parametrize(
    "expected,student,n,ok",
    [
        ("2.675", "2.68", 2, True),  # an exact tie rounds half-even: 2.675 -> 2.68
        ("2.665", "2.66", 2, True),  # 2.665 -> 2.66
        ("2.665", "2.67", 2, False),
        ("200/343", "-0.583", 3, False),
        ("-200/343", "-0.583", 3, True),
        ("-200/343", "-0.58", 3, False),
        ("-200/343", "-0.5831", 3, True),  # the student's decimal is rounded too
        ("1/3", "0.333", 3, True),
        ("1/3", "0.334", 3, False),
        ("2/3", "0.667", 3, True),
        ("1/2", "0", 0, True),  # 0.5 -> 0 (half-even)
        ("3/2", "2", 0, True),  # 1.5 -> 2
        ("-1/2", "0", 0, True),
        ("-5/2", "-2", 0, True),
        ("7", "7.000", 3, True),
    ],
)
def test_round_matches(expected: str, student: str, n: int, ok: bool) -> None:
    assert round_matches(Rational(expected), Decimal(student), n) is ok


def test_round_matches_large_decimals_never_hit_context_precision() -> None:
    # 30 significant digits with an exponent of 30 exceed decimal's default 28-digit context.
    big = Decimal("123456789012345678901234567890E30")
    assert round_matches(Rational(int(big)), big, 10) is True
    assert round_matches(Rational(int(big)) + 1, big, 10) is False


def test_round_matches_tiny_decimal() -> None:
    assert round_matches(Rational(1, 10**30), Decimal("1E-30"), 3) is True
    assert round_matches(Rational(1, 10**30), Decimal("0.001"), 3) is False
