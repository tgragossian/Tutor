"""Allowlisted LaTeX -> MathJSON parser for the leak guard (C1 Task 2).

``test_bank_answers_roundtrip`` uses SymPy: it imports ``mathtutor.verify.check`` directly,
which tests may do; the parser module itself must not (see ``test_parser_imports``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import ChoiceAnswer, ExpressionAnswer
from mathtutor.domain import VerdictStatus
from mathtutor.help import latex_parse
from mathtutor.help.config import load_help_config
from mathtutor.help.latex_parse import ParsedMath, ParseRejected, parse_latex
from mathtutor.verify.check import check
from mathtutor.verify.structure import check_structure
from mathtutor.verify.types import CheckRequest, SubmittedAnswer, Verdict

ROOT = Path(__file__).parents[3]
CONTENT = ROOT / "content" / "compiled" / "problems.json"
CONFIG = ROOT / "src" / "mathtutor" / "help" / "help_config.json"


def _parsed(src: str, variable: str = "x") -> ParsedMath:
    result = parse_latex(src, variable=variable)
    assert isinstance(result, ParsedMath), (src, result)
    return result


def _cases() -> list[tuple[str, object, str, str]]:
    """(label, spec, kind, latex) for every answer and every choice in the bank."""
    cases: list[tuple[str, object, str, str]] = []
    for p in load_bundle(CONTENT).bundle.problems:
        a = p.answer
        if isinstance(a, ChoiceAnswer):
            for c in a.choices:
                spec = ExpressionAnswer(kind="expression", latex=c.latex, mathjson=c.mathjson)
                cases.append((f"{p.id}/{c.id}", spec, "expression", c.latex))
        else:
            cases.append((p.id, a, a.kind, a.latex))
    return cases


CASES = _cases()


def test_bank_has_22_problems() -> None:
    assert len({label.split("/")[0] for label, *_ in CASES}) == 22


@pytest.mark.parametrize(("label", "spec", "kind", "latex"), CASES, ids=[c[0] for c in CASES])
def test_bank_answers_roundtrip(label: str, spec: object, kind: str, latex: str) -> None:
    parsed = _parsed(latex)
    assert parsed.foreign == frozenset()
    answer = SubmittedAnswer(kind, parsed.tree, latex, None)  # type: ignore[arg-type]
    result = check(CheckRequest(spec, answer), deadline_s=10.0)  # type: ignore[arg-type]
    assert isinstance(result.outcome, Verdict), (label, result.outcome)
    assert result.outcome.status is VerdictStatus.CORRECT, (label, result.outcome)


@pytest.mark.parametrize(
    "src",
    [
        r"2x\cos x - x^2\sin x",
        r"x(2\cos x - x\sin x)",
        r"\left(3x^2+1\right)^{2}",
        r"6x\cdot(x^2+1)^2",
        r"\dfrac{1}{x}",
        r"\tfrac12 x^{-1/2}",
        r"\sqrt[3]{x}",
        r"\sin^2 x",
        r"\sec x\tan x",
        r"e^{2x}",
        r"\ln|x|",
        r"-\frac{200}{49}",
        r"0.54",
    ],
)
def test_notation_table(src: str) -> None:
    assert _parsed(src).foreign == frozenset()


@pytest.mark.parametrize(
    ("src", "tree"),
    [
        (r"\sin 7x", ["Sin", ["Multiply", 7, "x"]]),
        (r"\sec x\tan x", ["Multiply", ["Sec", "x"], ["Tan", "x"]]),
        (r"\sin^2 x", ["Power", ["Sin", "x"], 2]),
        (r"\sqrt[3]{x}", ["Root", "x", 3]),
        (
            r"\tfrac12 x^{-1/2}",
            ["Multiply", ["Divide", 1, 2], ["Power", "x", ["Negate", ["Divide", 1, 2]]]],
        ),
        (r"\ln|x|", ["Ln", ["Abs", "x"]]),
        (r"-\frac{200}{49}", ["Negate", ["Divide", 200, 49]]),
        (r"0.54", {"num": "0.54"}),
        (r"e^{2x}", ["Power", "ExponentialE", ["Multiply", 2, "x"]]),
        (r"\sin(x)^2", ["Power", ["Sin", "x"], 2]),
        (r"\sin x^2", ["Sin", ["Power", "x", 2]]),
        (r"\log_{2} 8", ["Log", 8, 2]),
        (r"1 - x + 2", ["Add", ["Subtract", 1, "x"], 2]),
        (r"\left|x - 1\right| |x|", ["Multiply", ["Abs", ["Subtract", "x", 1]], ["Abs", "x"]]),
        (r"\pi x", ["Multiply", "Pi", "x"]),
    ],
)
def test_trees(src: str, tree: object) -> None:
    assert _parsed(src).tree == tree


@pytest.mark.parametrize(
    ("src", "foreign"),
    [
        (r"3u^2", {"u"}),
        (r"f'(x)", {"f'"}),
        (r"\frac{d}{dx}(x^2)", {"d/dx"}),
        (r"g(x)h'(x)", {"g", "h'"}),
        (r"\frac{dy}{dx}", {"dy/dx"}),
        (r"\theta + x", {"theta"}),
        (r"x_0", {"x_0"}),
        (r"t^2", {"t"}),
    ],
)
def test_foreign_symbols(src: str, foreign: set[str]) -> None:
    assert _parsed(src).foreign == frozenset(foreign)


def test_variable_is_not_foreign() -> None:
    assert _parsed(r"t^2", variable="t").foreign == frozenset()
    assert _parsed(r"x^2", variable="t").foreign == frozenset({"x"})


@pytest.mark.parametrize(
    "src",
    [
        r"\begin{matrix} 1 \end{matrix}",
        r"\int x\,dx",
        r"\lim_{x\to0} x",
        r"\frac{1}{x",
        r"(x+1",
        r"x+1)",
        r"x^{",
        "x" * 401,
        "(" * 25 + "x" + ")" * 25,
        "+".join(["x"] * 200),
        r"\sin^{-1} x",
        r"x = 2",
        r"x^2^3",
        r"",
        r"\sin",
        r"2 +",
    ],
)
def test_rejects(src: str) -> None:
    result = parse_latex(src)
    assert isinstance(result, ParseRejected), src
    assert result.reason


def test_limit_reasons() -> None:
    assert parse_latex("(" * 25 + "x" + ")" * 25) == ParseRejected("nested too deeply")
    assert parse_latex("+".join(["x"] * 200)) == ParseRejected("too many nodes")


@pytest.mark.parametrize("src", [r"1/2x", r"x \div 2x", r"1/2\sin x", r"x/2(x+1)", r"1/2^3x"])
def test_rejects_ambiguous_division(src: str) -> None:
    assert parse_latex(src) == ParseRejected("ambiguous inline division")


@pytest.mark.parametrize(
    ("src", "tree"),
    [
        (r"\frac{1}{2x}", ["Divide", 1, ["Multiply", 2, "x"]]),
        (r"1/(2x)", ["Divide", 1, ["Multiply", 2, "x"]]),
        (r"(1/2)x", ["Multiply", ["Divide", 1, 2], "x"]),
        (r"x/2", ["Divide", "x", 2]),
        (r"x/2 + 1", ["Add", ["Divide", "x", 2], 1]),
        (r"x/2\cdot x", ["Multiply", ["Divide", "x", 2], "x"]),
        (r"2x/3", ["Divide", ["Multiply", 2, "x"], 3]),
    ],
)
def test_explicit_division(src: str, tree: object) -> None:
    assert _parsed(src).tree == tree


@pytest.mark.parametrize("src", [r"x2", r"{2}3", r"2.5.3", r"1e5", r"x^23", r"2\,3", r"2 3"])
def test_rejects_juxtaposed_number(src: str) -> None:
    result = parse_latex(src)
    assert isinstance(result, ParseRejected), src
    assert result.reason in ("number after a factor", "spaced digits")


@pytest.mark.parametrize(
    ("src", "tree"),
    [
        (r"2x", ["Multiply", 2, "x"]),
        (r"2\pi", ["Multiply", 2, "Pi"]),
        (r"3(x+1)", ["Multiply", 3, ["Add", "x", 1]]),
        (r"x^2", ["Power", "x", 2]),
        (r"2\cdot 3", ["Multiply", 2, 3]),
        (r"\frac12", ["Divide", 1, 2]),
        (r"\sqrt2 x", ["Multiply", ["Sqrt", 2], "x"]),
        (r"2 x", ["Multiply", 2, "x"]),
        (r"12.5", {"num": "12.5"}),
    ],
)
def test_numbers_before_factors(src: str, tree: object) -> None:
    assert _parsed(src).tree == tree


def test_limits_are_inclusive() -> None:
    assert isinstance(parse_latex("+".join(["x"] * 199)), ParsedMath)  # 200 nodes
    assert isinstance(parse_latex("(" * 24 + "x" + ")" * 24), ParsedMath)
    assert isinstance(parse_latex("1" + " " * 399), ParsedMath)  # 400 bytes


def test_rejection_reason_does_not_echo_input() -> None:
    result = parse_latex(r"\secretcommand{hidden}")
    assert isinstance(result, ParseRejected)
    assert "secret" not in result.reason and "hidden" not in result.reason


def test_constants_match_config() -> None:
    cfg = load_help_config(CONFIG)
    assert latex_parse.MAX_BYTES == cfg.guard.max_candidate_bytes
    assert latex_parse.MAX_NODES == cfg.guard.max_nodes
    assert latex_parse.MAX_DEPTH == cfg.guard.max_depth
    assert latex_parse.PARSER_VERSION == cfg.parser_version
    assert json.loads(CONFIG.read_text(encoding="utf-8"))["parser_version"] == "1"


def test_parser_imports() -> None:
    # The guard parses in the web process: no SymPy, mpmath or verifier check there.
    script = (
        "import sys, mathtutor.help.latex_parse\n"
        "banned = ('sympy', 'mpmath', 'mathtutor.verify.check')\n"
        "bad = sorted(n for n in sys.modules if any(n == b or n.startswith(b + '.') "
        "for b in banned))\n"
        "print(bad); sys.exit(1 if bad else 0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr


@settings(max_examples=500, deadline=None)
@given(st.text(alphabet=st.characters(codec="utf-8"), max_size=400))
def test_never_raises(src: str) -> None:
    src = src.encode("utf-8")[:400].decode("utf-8", errors="ignore")  # at most 400 bytes
    result = parse_latex(src)
    assert isinstance(result, ParsedMath | ParseRejected)
    if isinstance(result, ParseRejected):
        assert not result.reason.startswith("internal error"), result.reason


_PIECES = [*"0123456789xyefu+-*/^_{}()[]|.' ", r"\frac", r"\sqrt", r"\sin", r"\cos", r"\ln"]
_PIECES += [r"\log", r"\left(", r"\right)", r"\left|", r"\right|", r"\cdot", r"\pi"]


@settings(max_examples=1000, deadline=None)
@given(st.lists(st.sampled_from(_PIECES), max_size=60).map("".join))
def test_never_raises_latexish(src: str) -> None:
    # LaTeX-like noise reaches the grammar; any tree it accepts passes the checker's bounds.
    result = parse_latex(src)
    assert isinstance(result, ParsedMath | ParseRejected)
    if isinstance(result, ParseRejected):
        assert not result.reason.startswith("internal error"), result.reason
    else:
        assert check_structure(result.tree) is None
