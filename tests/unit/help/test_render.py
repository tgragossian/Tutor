"""Safe HTML for delivered help text (Task 11)."""

from __future__ import annotations

from mathtutor.help.leak_guard import split_spans
from mathtutor.help.render import render_help_html


def test_render_escapes() -> None:
    html = render_help_html("<script>alert(1)</script> [x](http://a) ![i](u) and $x^2$")
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "[x](http://a)" in html and "![i](u)" in html
    assert "<a" not in html and "<img" not in html and "href" not in html
    assert "<math-field read-only>x^2</math-field>" in html


def test_paragraphs_and_bold() -> None:
    html = render_help_html("First **idea** here.\n\nSecond line.")
    assert html == "<p>First <strong>idea</strong> here.</p><p>Second line.</p>"


def test_math_latex_is_escaped_inside_the_field() -> None:
    html = render_help_html(r"Try $a<b \text{</math-field><script>}$ now")
    assert "<script>" not in html
    assert (
        r"<math-field read-only>a&lt;b \text{&lt;/math-field&gt;&lt;script&gt;}</math-field>"
        in html
    )


def test_only_guard_delimiters_render_as_math() -> None:
    html = render_help_html(r"Display $$\frac{1}{2}$$ and \(y\) and \[z\]")
    assert html.count("<math-field read-only>") == 3
    assert r"<math-field read-only>\frac{1}{2}</math-field>" in html


def test_escaped_dollar_is_literal_text() -> None:
    assert render_help_html(r"It costs \$5 \% \& \#.") == "<p>It costs $5 % &amp; #.</p>"


def test_malformed_math_renders_as_plain_text() -> None:
    html = render_help_html("unbalanced $x^2 and <b>")
    assert "<math-field" not in html
    assert html == "<p>unbalanced $x^2 and &lt;b&gt;</p>"


def test_bold_does_not_reach_into_math() -> None:
    html = render_help_html("**see $a**b$ here**")
    assert "<math-field read-only>a**b</math-field>" in html
    assert html.startswith("<p><strong>see ")


def test_quotes_and_ampersands_escaped() -> None:
    assert render_help_html("a \"b\" & 'c'") == "<p>a &quot;b&quot; &amp; &#x27;c&#x27;</p>"


def test_blank_input_is_empty() -> None:
    assert render_help_html("  \n\n ") == ""


def test_math_fields_match_guard_spans() -> None:
    texts = (
        r"a $x$ b $$y$$ \(z\) \[w\] \$5",
        "plain",
        r"$a$$b$",
        "$x=1$, then $y$.",
        "See $\x00$ 18x times stuff $\x00$ ok",  # the reviewer's NUL probe
        "\x000\x00 $q$ and \x001\x00",  # placeholder look-alikes in prose
    )
    for text in texts:
        spans = [k for k, _ in split_spans(text) if k != "prose"]
        assert render_help_html(text).count("<math-field read-only>") == len(spans)


def test_prose_nul_is_not_a_placeholder() -> None:
    html = render_help_html("\x000\x00 then $q$")
    assert html.count("<math-field read-only>q</math-field>") == 1
    assert "\x00" not in html
