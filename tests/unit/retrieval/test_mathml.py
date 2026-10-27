"""MathML -> LaTeX on real snippets from the OpenStax snapshot (tests/fixtures/corpus)."""

import json
from pathlib import Path

import pytest

from mathtutor.retrieval.mathml import PLACEHOLDER, mathml_string_to_latex

SNIPPETS = json.loads(
    (
        Path(__file__).resolve().parents[2] / "fixtures" / "corpus" / "mathml_snippets.json"
    ).read_text(encoding="utf-8")
)

EXPECTED = {
    "abs_table": r"\frac{dy}{dx}|\begin{array}{l} \\ {}_{x = a}\end{array}",
    "aligned": r"\begin{array}{l}\sin\,\theta = \frac{y}{r} \\ y = r\,\sin\,\theta.\end{array}",
    "bar": r"\overline{x}",
    "cdot": r"f\cdot g",
    "degree": r"0^{\circ}",
    "dollar": r"\$P",
    "frac": r"\frac{3}{2}",
    "int_bounds": r"\int_{0}^{1}tdt",
    "lim": r"\lim_{x \to 2}x",
    "mfenced": r"\tan(x)",
    "mfenced_abs": r"2\ln|x|+C\text{ or }\ln(x^{2})+C",
    "mpadded": r"y = e^{2x}",
    "mspace": r"\:\times\:",
    "msub": r"v_{0}",
    "neq_inf": r"x \ne 0",
    "paren_table": (
        r"(\begin{array}{l}n \\ k\end{array}) = "
        r"\frac{n(n-1)(n-2)\cdots(n-k+1)}{k(k-1)(k-2)\cdots3\cdot2\cdot1} = \frac{n!}{k!(n-k)!}"
    ),
    "piecewise": r"f(x) = \begin{cases}3, x < 1 \\ 3x, x \ge 1\end{cases}",
    "prime": r"f'",
    "root": r"\sqrt[3]{x}",
    "sqrt": r"\sqrt{3}",
    "sum": r"\sum_{i = 1}^{10}i",
    "sum_mstyle": r"M = \sum_{i = 1}^{n}m_{i}x_{i}",
    "trig_pow": r"g(x) = \sin^{-1}x,",
    "underbrace": (r"\int{\underbrace{(x^{2}-3)}_{u}}^{3}\underbrace{(2xdx)}_{du} = \int u^{3}du."),
}


def test_every_snippet_has_an_expectation() -> None:
    assert set(SNIPPETS) == set(EXPECTED)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_snippet_converts(name: str) -> None:
    result = mathml_string_to_latex(SNIPPETS[name]["mathml"])
    assert result.unavailable == 0
    assert result.latex == EXPECTED[name]


def test_annotation_branch_is_ignored() -> None:
    src = (
        "<math><semantics><mrow><mi>x</mi></mrow>"
        "<annotation-xml encoding='MathML-Content'><mi>y</mi></annotation-xml></semantics></math>"
    )
    assert mathml_string_to_latex(src).latex == "x"


def test_unknown_element_is_counted_placeholder() -> None:
    src = (
        "<math><semantics><mrow><mi>x</mi><menclose><mi>y</mi></menclose></mrow></semantics></math>"
    )
    result = mathml_string_to_latex(src)
    assert result.unavailable == 1
    assert result.latex == "x" + PLACEHOLDER


def test_malformed_input_never_raises() -> None:
    assert mathml_string_to_latex("<math><mfrac>").unavailable == 1
    bad_arity = "<math><semantics><mfrac><mi>x</mi></mfrac></semantics></math>"
    assert mathml_string_to_latex(bad_arity).unavailable == 1


def test_comma_between_numbers_stays_unspaced() -> None:
    money = "<math><semantics><mrow><mn>1</mn><mo>,</mo><mn>502.08</mn></mrow></semantics></math>"
    pair = "<math><semantics><mrow><mi>x</mi><mo>,</mo><mi>y</mi></mrow></semantics></math>"
    assert mathml_string_to_latex(money).latex == "1,502.08"
    assert mathml_string_to_latex(pair).latex == "x, y"


def test_prose_mtext_is_escaped() -> None:
    src = "<math><semantics><mrow><mtext>cost in $ &amp; 50%</mtext></mrow></semantics></math>"
    assert mathml_string_to_latex(src).latex == r"\text{ cost in \$ \& 50\%}"
