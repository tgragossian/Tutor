from __future__ import annotations

import pytest

from mathtutor.verify.latex_rules import FUNCTION_PARENS_DETAIL, unparenthesized_function


@pytest.mark.parametrize(
    ("tex", "expected"),
    [
        (r"\sin x", r"\sin"),
        (r"\cos x(x+1)", r"\cos"),
        (r"\cos^2x", r"\cos"),
        (r"\ln 2", r"\ln"),
        (r"\log_2 8", r"\log"),
        (r"(1-\sin x)^2", r"\sin"),
        (r"\tan\frac{x}{3}", r"\tan"),
        (r"\exp x", r"\exp"),
        (r"\sin(x)+\cos x", r"\cos"),
        (r"\operatorname{sin}x", r"\operatorname{sin}"),
        (r"\mathrm{cos}x", r"\mathrm{cos}"),
        (r"\operatorname{ln}2", r"\operatorname{ln}"),
        (r"\mathrm{ sin }x", r"\mathrm{sin}"),
        (r"\operatorname{\mathrm{sin}}x", r"\operatorname{sin}"),
    ],
)
def test_rejects(tex: str, expected: str) -> None:
    assert unparenthesized_function(tex) == expected


@pytest.mark.parametrize(
    "tex",
    [
        r"\sin(x)",
        r"\sin\left(x\right)",
        r"\sin^2(x)",
        r"\sin^{2}\left(x\right)",
        r"\log_2(8)",
        r"\log_{10}(x)",
        r"\ln\lvert x\rvert",
        r"\ln\left|x\right|",
        r"\ln|x|",
        r"\sin (x)",
        r"\sin\,(x)",
        r"\sinh x",
        r"\operatorname{sin}(x)",
        r"\mathrm{sin}\left(x\right)",
        r"\operatorname{sin}^2(x)",
        r"\operatorname{\mathrm{sin}}(x)",
        r"\mathrm{d}x",
        r"\operatorname{lcm}(a)",
        r"\operatorname{lcm}a",
        r"\mathrm{e}^{x}",
        r"\lnot",
        r"\left(x\right)",
        r"x^2+1",
        r"e^{x}",
        "",
    ],
)
def test_accepts(tex: str) -> None:
    assert unparenthesized_function(tex) is None


def test_detail_copy() -> None:
    assert FUNCTION_PARENS_DETAIL == "Put the function's input in parentheses, like sin(x)."
