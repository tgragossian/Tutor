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
    "abs_table": r"\left.\frac{dy}{dx}\right|_{x = a}",
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
    "mspace": r"\times",
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


def m(body: str) -> str:
    src = f"<math><semantics><mrow>{body}</mrow></semantics></math>"
    return mathml_string_to_latex(src).latex


def test_compound_base_is_braced() -> None:
    assert m("<msup><mrow><mi>x</mi><mo>+</mo><mn>1</mn></mrow><mn>2</mn></msup>") == "{x+1}^{2}"


def test_one_sided_limit_and_starred_subscript() -> None:
    assert m("<mi>x</mi><mo>→</mo><msup><mi>a</mi><mo>−</mo></msup>") == r"x \to a^{-}"
    assert m("<msubsup><mi>x</mi><mi>i</mi><mo>*</mo></msubsup>") == "x_{i}^{*}"


def test_units_are_not_functions() -> None:
    assert m("<mn>0.5</mn><mi>Ω</mi><mo>/</mo><mtext>min</mtext>") == r"0.5\Omega/\text{ min }"
    assert m("<mn>5</mn><mspace width='0.2em'/><mtext>sec</mtext>") == r"5\:\text{ sec }"
    assert m("<mn>5</mn><mtext>sec</mtext><mo>,</mo>") == r"5\text{ sec },"
    assert m("<mtext>sec</mtext><mspace width='0.1em'/><mi>x</mi>") == r"\sec\,x"
    assert m("<msup><mtext>sec</mtext><mn>2</mn></msup><mi>x</mi>") == r"\sec^{2}x"
    assert m("<mtext>min</mtext><mo>(</mo><mi>a</mi><mo>)</mo>") == r"\min(a)"
    inverse = "<msup><mrow><mtext>sec</mtext></mrow><mn>−1</mn></msup><mi>x</mi>"
    assert m(f"<mi>d</mi><mspace width='0.1em'/>{inverse}") == r"d\,\sec^{-1}x"


def test_multi_letter_identifier_is_plain() -> None:
    assert m("<mi>dx</mi>") == "dx"
    assert m("<mi>units</mi>") == r"\text{ units }"


def test_no_dangling_backslash() -> None:
    assert m("<mi>x</mi><mtext> </mtext>") == "x"
    assert m("<mspace width='1em'/><mi>x</mi>") == "x"
    assert m("<mi>x</mi><mspace width='0.1em'/>") == "x"


def test_evaluation_bar_without_left_operand() -> None:
    bar = (
        "<mo>|</mo><mtable><mtr><mtd><msup><mrow/><mn>2</mn></msup></mtd></mtr>"
        "<mtr><mtd><msub><mrow/><mn>0</mn></msub></mtd></mtr></mtable>"
    )
    assert m(bar) == r"\Big|_{0}^{2}"
