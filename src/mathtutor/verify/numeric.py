"""The decimal rounding rule (spec 02), in exact rational arithmetic."""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import sympy


def round_half_even(value: Fraction, decimals: int) -> int:
    """``value`` rounded to ``decimals`` places with ROUND_HALF_EVEN, scaled by 10**decimals."""
    scaled: Fraction = value * Fraction(10**decimals)
    floor = scaled.numerator // scaled.denominator
    rest = scaled - floor
    if rest > Fraction(1, 2) or (rest == Fraction(1, 2) and floor % 2 == 1):
        return floor + 1
    return floor


def round_matches(expected: sympy.Rational, student: Decimal, decimals: int) -> bool:
    """True iff both values round to the same number at ``decimals`` places (ROUND_HALF_EVEN).

    Both sides are exact rationals, so no decimal context precision or float is involved.
    """
    want = Fraction(int(expected.p), int(expected.q))
    got = Fraction(student)  # exact; raises on NaN or infinity
    return round_half_even(want, decimals) == round_half_even(got, decimals)


def rounded_cell(lo: Fraction, hi: Fraction, decimals: int) -> int | None:
    """The rounding of every value in ``[lo, hi]`` (scaled by 10**decimals), or None.

    Rounding is monotone, so when both ends round to the same cell every value between them
    does too; otherwise the enclosure meets a cell boundary and nothing is certified.
    """
    cell = round_half_even(lo, decimals)
    return cell if cell == round_half_even(hi, decimals) else None
