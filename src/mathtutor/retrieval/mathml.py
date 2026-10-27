"""Presentation MathML -> LaTeX, covering what OpenStax Calculus Volume 1 actually uses.

The archive pages carry MathML only (no TeX annotation), so the corpus builder converts the
first child of each ``<semantics>`` element.  Stdlib only: this module is importable by the web
process.  Conversion never raises: an element it does not know becomes the placeholder
``\\text{[math unavailable]}`` and is counted in :attr:`MathResult.unavailable`, so the build can
report it instead of silently dropping math.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

PLACEHOLDER = r"\text{[math unavailable]}"

FUNCTIONS = frozenset(
    "sin cos tan cot sec csc sinh cosh tanh coth arcsin arccos arctan ln log exp lim "
    "max min sup inf det gcd".split()
)
OPERATOR_NAMES = frozenset("sech csch".split())
AMBIGUOUS = frozenset("min max sec".split())
# A word followed by one of these (or by nothing) is a unit, not an applied function.
NOT_AN_ARGUMENT = frozenset(list(",.;:)]}/=<>") + ["−", "-", "+", "·", "×", "≤", "≥"])
BIG_OPERATORS = frozenset([r"\lim", r"\sum", r"\int", r"\prod", r"\max", r"\min", r"\sup", r"\inf"])

GREEK = {
    "α": r"\alpha",
    "β": r"\beta",
    "γ": r"\gamma",
    "δ": r"\delta",
    "ε": r"\varepsilon",
    "ϵ": r"\epsilon",
    "ζ": r"\zeta",
    "η": r"\eta",
    "θ": r"\theta",
    "ι": r"\iota",
    "κ": r"\kappa",
    "λ": r"\lambda",
    "μ": r"\mu",
    "ν": r"\nu",
    "ξ": r"\xi",
    "π": r"\pi",
    "ρ": r"\rho",
    "σ": r"\sigma",
    "τ": r"\tau",
    "υ": r"\upsilon",
    "φ": r"\varphi",
    "ϕ": r"\phi",
    "χ": r"\chi",
    "ψ": r"\psi",
    "ω": r"\omega",
    "Γ": r"\Gamma",
    "Δ": r"\Delta",
    "Θ": r"\Theta",
    "Λ": r"\Lambda",
    "Ξ": r"\Xi",
    "Π": r"\Pi",
    "Σ": r"\Sigma",
    "Φ": r"\Phi",
    "Ψ": r"\Psi",
    "Ω": r"\Omega",
    "Α": "A",
    "Β": "B",
}
SYMBOLS = {
    "−": "-",
    "–": "-",
    "—": "-",
    "·": r"\cdot",
    "⋅": r"\cdot",
    "×": r"\times",
    "→": r"\to",
    "⇒": r"\Rightarrow",
    "≤": r"\le",
    "≥": r"\ge",
    "≠": r"\ne",
    "≈": r"\approx",
    "∈": r"\in",
    "∫": r"\int",
    "∑": r"\sum",
    "′": "'",
    "″": "''",
    "‴": "'''",
    "∘": r"\circ",
    "◦": r"\circ",
    "±": r"\pm",
    "∓": r"\mp",
    "∪": r"\cup",
    "∩": r"\cap",
    "∞": r"\infty",
    "⋯": r"\cdots",
    "…": r"\ldots",
    "⋮": r"\vdots",
    "ℝ": r"\mathbb{R}",
    "∴": r"\therefore",
    "∼": r"\sim",
    "~": r"\sim",
    "⌊": r"\lfloor",
    "⌋": r"\rfloor",
    "{": r"\{",
    "}": r"\}",
    "\xa0": r"\ ",
    "¢": r"\text{¢}",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "&": r"\&",
    "_": r"\_",
    "°": r"^{\circ}",
    "ℓ": r"\ell",
    "⏟": "",
    "⁡": "",
    "⁢": "",
    "⁣": "",
    " ": r"\,",
    "​": "",
    "\\": r"\backslash",
    "^": r"\hat{}",
}
CHARS = {**GREEK, **SYMBOLS}
RELATIONS = frozenset(
    ["=", "<", ">", r"\le", r"\ge", r"\ne", r"\approx", r"\to", r"\Rightarrow", r"\in"]
)
TEXT_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "%": r"\%",
    "&": r"\&",
    "#": r"\#",
    "_": r"\_",
    "^": r"\^{}",
    "~": r"\~{}",
    "\xa0": " ",
    "−": "-",
    "–": "-",
}
OVERLINES = frozenset(["–", "¯", "‾", "-", "−", "_"])
ACCENTS = {
    "→": r"\vec",
    "^": r"\hat",
    "ˆ": r"\hat",
    "~": r"\tilde",
    "˜": r"\tilde",
    "˙": r"\dot",
    ".": r"\dot",
}
TRANSPARENT = frozenset(["mrow", "mstyle", "mpadded", "semantics", "math"])
_WORD = re.compile(r"[A-Za-z]{2,}")
_ENDS_COMMAND = re.compile(r"\\[A-Za-z]+$")
_UNDERLINE_RUN = re.compile(r"_{3,}")


@dataclass(frozen=True)
class MathResult:
    latex: str
    unavailable: int


def local(tag: str) -> str:
    """Element name without its XML namespace."""
    return tag.rsplit("}", 1)[-1]


def join(parts: list[str]) -> str:
    """Concatenate LaTeX pieces, adding a space only where a command would run into a letter."""
    out = ""
    for part in parts:
        if not part:
            continue
        if out and _ENDS_COMMAND.search(out) and part[0].isalpha():
            out += " "
        out += part
    return out


def convert_chars(text: str) -> str:
    """Math-mode conversion of a run of characters (mi/mn/mo text)."""
    text = _UNDERLINE_RUN.sub("\x00", text)
    parts: list[str] = []
    for ch in text:
        if ch == "\x00":
            parts.append(r"\underline{\qquad}")
        elif ch in RELATIONS or SYMBOLS.get(ch) in RELATIONS:
            parts.append(" " + SYMBOLS.get(ch, ch) + " ")
        elif ch == ",":
            parts.append(", ")
        else:
            parts.append(CHARS.get(ch, ch))
    return join(parts)


def text_mode(text: str) -> str:
    return r"\text{" + "".join(TEXT_ESCAPES.get(ch, ch) for ch in text) + "}"


def word(text: str, *, applied: bool = True) -> str:
    """mi/mtext content: function names become commands, prose becomes \\text{...}.

    ``min``/``max``/``sec`` are also units (minutes, seconds); they become commands only when
    ``applied`` to an argument.
    """
    bare = text.replace("\xa0", " ").strip()
    if bare in AMBIGUOUS and not applied:
        return text_mode(" " + bare + " ")
    if bare in FUNCTIONS:
        return "\\" + bare
    if bare in OPERATOR_NAMES:
        return r"\operatorname{" + bare + "}"
    if not bare:
        return r"\ " if text else ""
    if _WORD.search(bare):
        # Words glued to math ("x\text{or}y") read badly: pad a side that starts/ends a word.
        prose = text.replace("\xa0", " ")
        if prose[0].isalpha():
            prose = " " + prose
        if prose[-1].isalpha():
            prose += " "
        return text_mode(prose)
    return convert_chars(text.replace("\xa0", " ").strip() if text.strip() else text)


def _is_mo(el: ET.Element, text: str) -> bool:
    return local(el.tag) == "mo" and (el.text or "").strip() == text


class _Converter:
    def __init__(self) -> None:
        self.unavailable = 0
        self.units: set[int] = set()  # ids of min/max/sec words used as units

    def kids(self, el: ET.Element) -> list[ET.Element]:
        return [c for c in el if local(c.tag) != "annotation-xml"]

    def unwrap(self, el: ET.Element) -> ET.Element:
        while local(el.tag) in TRANSPARENT:
            kids = self.kids(el)
            if len(kids) != 1:
                break
            el = kids[0]
        return el

    def needs_group(self, el: ET.Element) -> bool:
        el = self.unwrap(el)
        tag = local(el.tag)
        text = (el.text or "").strip()
        if tag in ("mi", "mtext"):
            return len(text) > 1 and text not in FUNCTIONS
        if tag in ("mn", "msqrt", "mroot", "mfrac", "mfenced", "msub", "msup", "msubsup"):
            return False
        if tag == "mo":
            return len(text) > 1
        if tag in TRANSPARENT:
            kids = self.kids(el)
            if not kids:
                return False
            first, last = kids[0], kids[-1]
            if (
                local(first.tag) == "mo"
                and local(last.tag) == "mo"
                and (first.text or "").strip() in "([|"
                and (last.text or "").strip() in ")]|"
            ):
                return False
        return True

    def base(self, el: ET.Element) -> str:
        latex = self.conv(el)
        if not latex:
            return "{}"
        return "{" + latex + "}" if self.needs_group(el) else latex

    def row(self, el: ET.Element) -> str:
        kids = self.kids(el)
        parts: list[str] = []
        i = 0
        while i < len(kids):
            k = kids[i]
            nxt = kids[i + 1] if i + 1 < len(kids) else None
            if (
                local(k.tag) == "mo"
                and (k.text or "").strip() == "{"
                and nxt is not None
                and local(self.unwrap(nxt).tag) == "mtable"
                and not any((c.text or "").strip() == "}" for c in kids[i + 2 :])
            ):
                parts.append(self.table(self.unwrap(nxt), env="cases"))
                i += 2
                continue
            prev = kids[i - 1] if i else None
            if (
                local(k.tag) == "mo"
                and (k.text or "").strip() == ","
                and prev is not None
                and nxt is not None
                and local(prev.tag) == "mn"
                and local(nxt.tag) == "mn"
            ):
                # "1,502.08" or "[0,100]": the source does not say which, so keep it unspaced.
                parts.append(",")
                i += 1
                continue
            bar, used = self.evaluation_bar(k, nxt)
            if bar is not None:
                # "f(x) |_{x=a}" is a one-row table under a bar: \left. f(x) \right|_{x=a}.
                before = join(parts).strip()
                parts = [r"\left." + before + r"\right|" + bar] if before else [r"\Big|" + bar]
                i += used
                continue
            if local(k.tag) in ("mi", "mtext") and (k.text or "").strip() in AMBIGUOUS:
                arg = next((c for c in kids[i + 1 :] if local(c.tag) != "mspace"), None)
                has_before = any(local(c.tag) != "mspace" for c in kids[:i])
                # A lone word in a wrapper row (an msup base) takes its context from outside.
                if has_before and (
                    arg is None
                    or (local(arg.tag) == "mo" and (arg.text or "").strip() in NOT_AN_ARGUMENT)
                ):
                    self.units.add(id(k))
            parts.append(self.conv(k))
            i += 1
        return join(parts)

    def evaluation_bar(self, k: ET.Element, nxt: ET.Element | None) -> tuple[str | None, int]:
        """Scripts of an evaluation bar ``|`` + table of empty-based scripts, and kids used."""
        if _is_mo(k, "|") and nxt is not None:
            scripts = self.bar_scripts(self.unwrap(nxt))
            return (scripts, 2) if scripts is not None else (None, 0)
        inner = self.unwrap(k)
        inner_kids = self.kids(inner)
        if local(inner.tag) == "mrow" and len(inner_kids) == 2 and _is_mo(inner_kids[0], "|"):
            scripts = self.bar_scripts(self.unwrap(inner_kids[1]))
            return (scripts, 1) if scripts is not None else (None, 0)
        return None, 0

    def bar_scripts(self, table: ET.Element) -> str | None:
        if local(table.tag) != "mtable":
            return None
        sub = sup = ""
        for tr in self.kids(table):
            cells = self.kids(tr)
            if local(tr.tag) != "mtr" or len(cells) != 1:
                return None
            content = self.kids(cells[0])
            if len(content) > 1:
                return None
            cell = self.unwrap(content[0]) if content else cells[0]
            tag = local(cell.tag)
            if not content or (tag in TRANSPARENT and not self.kids(cell)):
                continue
            scripts = self.kids(cell)
            arity = {"msub": 2, "msup": 2, "msubsup": 3}.get(tag)
            if arity is None or len(scripts) != arity:
                return None
            base = self.unwrap(scripts[0])
            if local(base.tag) not in TRANSPARENT or self.kids(base) or (base.text or "").strip():
                return None
            if tag in ("msub", "msubsup"):
                sub = self.conv(scripts[1])
            if tag == "msup":
                sup = self.conv(scripts[1])
            if tag == "msubsup":
                sup = self.conv(scripts[2])
        if not (sub or sup):
            return None
        return ("_{" + sub + "}" if sub else "") + ("^{" + sup + "}" if sup else "")

    def table(self, el: ET.Element, env: str = "array") -> str:
        rows: list[list[str]] = []
        aligns: list[str] = []
        for tr in self.kids(el):
            if local(tr.tag) not in ("mtr", "mlabeledtr"):
                rows.append([self.conv(tr)])
                continue
            cells = []
            for j, td in enumerate(self.kids(tr)):
                cells.append(self.conv(td).strip())
                al = td.get("columnalign")
                if al and len(aligns) <= j:
                    aligns.extend("l" for _ in range(j + 1 - len(aligns)))
                if al and aligns[j] == "l" and al != "left":
                    aligns[j] = al[0]
            rows.append(cells)
        ncols = max((len(r) for r in rows), default=1) or 1
        table_align = (el.get("columnalign") or "").split()
        spec = ""
        for j in range(ncols):
            if table_align:
                spec += table_align[min(j, len(table_align) - 1)][0]
            elif j < len(aligns):
                spec += aligns[j]
            else:
                spec += "l"
        body = r" \\ ".join(" & ".join(r) for r in rows)
        if env == "cases":
            return r"\begin{cases}" + body + r"\end{cases}"
        return r"\begin{array}{" + spec + "}" + body + r"\end{array}"

    def conv(self, el: ET.Element) -> str:
        tag = local(el.tag)
        kids = self.kids(el)
        text = el.text or ""
        if tag in TRANSPARENT or tag == "mtd":
            return self.row(el)
        applied = id(el) not in self.units
        if tag == "mi":
            bare = text.strip()
            if len(bare) <= 1:
                return convert_chars(bare)
            # One identifier: a function name, a word ("and", "units"), or letters ("dx").
            if bare in FUNCTIONS or bare in OPERATOR_NAMES or len(bare) >= 3:
                return word(text, applied=applied)
            return convert_chars(bare)
        if tag == "mn":
            return convert_chars(text.strip())
        if tag == "mo":
            return convert_chars(text if text.strip() == "" else text.strip())
        if tag == "mtext":
            return word(text, applied=applied)
        if tag == "mspace":
            return self.space(el)
        if tag == "mfrac" and len(kids) == 2:
            return r"\frac{" + self.conv(kids[0]) + "}{" + self.conv(kids[1]) + "}"
        if tag == "msqrt":
            return r"\sqrt{" + self.row(el) + "}"
        if tag == "mroot" and len(kids) == 2:
            return r"\sqrt[" + self.conv(kids[1]) + "]{" + self.conv(kids[0]) + "}"
        if tag in ("msup", "msub") and len(kids) == 2:
            script = self.conv(kids[1])
            if tag == "msup" and script and set(script) == {"'"}:
                return self.base(kids[0]) + script
            return self.base(kids[0]) + ("^" if tag == "msup" else "_") + "{" + script + "}"
        if tag == "msubsup" and len(kids) == 3:
            return self.base(kids[0]) + "_{" + self.conv(kids[1]) + "}^{" + self.conv(kids[2]) + "}"
        if tag == "mfenced":
            return self.fenced(el)
        if tag == "mtable":
            return self.table(el)
        if tag == "munder" and len(kids) == 2:
            return self.under(kids[0], kids[1])
        if tag == "mover" and len(kids) == 2:
            return self.over(kids[0], kids[1])
        if tag == "munderover" and len(kids) == 3:
            base = self.conv(kids[0])
            under, over = self.conv(kids[1]), self.conv(kids[2])
            if base in BIG_OPERATORS:
                return base + "_{" + under + "}^{" + over + "}"
            return r"\overset{" + over + r"}{\underset{" + under + "}{" + base + "}}"
        self.unavailable += 1
        return PLACEHOLDER

    def space(self, el: ET.Element) -> str:
        if el.get("linebreak") == "newline":
            return r"\quad "
        m = re.match(r"([\d.]+)em$", el.get("width") or "")
        if not m:
            return r"\ "
        width = float(m.group(1))
        if width < 0.19:
            return r"\,"
        if width < 0.25:
            return r"\:"
        if width < 0.5:
            return r"\;"
        return r"\quad " if width < 1.5 else r"\qquad "

    def fenced(self, el: ET.Element) -> str:
        open_ = convert_chars(el.get("open", "("))
        close = convert_chars(el.get("close", ")"))
        seps = (el.get("separators", ",") or "").replace(" ", "")
        parts: list[str] = []
        for i, k in enumerate(self.kids(el)):
            if i and seps:
                parts.append(convert_chars(seps[min(i - 1, len(seps) - 1)]))
            parts.append(self.conv(k))
        return open_ + join(parts) + close

    def under(self, base_el: ET.Element, under_el: ET.Element) -> str:
        under_txt = (under_el.text or "").strip()
        if local(under_el.tag) == "mo" and under_txt == "⏟":
            return r"\underbrace{" + self.conv(base_el) + "}"
        inner = self.unwrap(base_el)
        inner_kids = self.kids(inner)
        if (
            local(inner.tag) == "munder"
            and len(inner_kids) == 2
            and (inner_kids[1].text or "").strip() == "⏟"
        ):
            brace = r"\underbrace{" + self.conv(inner_kids[0]) + "}"
            return brace + "_{" + self.conv(under_el) + "}"
        base = self.conv(base_el)
        if base in BIG_OPERATORS:
            return base + "_{" + self.conv(under_el) + "}"
        return r"\underset{" + self.conv(under_el) + "}{" + base + "}"

    def over(self, base_el: ET.Element, over_el: ET.Element) -> str:
        mark = (over_el.text or "").strip() if local(over_el.tag) == "mo" else ""
        if mark in OVERLINES:
            return r"\overline{" + self.conv(base_el) + "}"
        if mark in ACCENTS:
            return ACCENTS[mark] + "{" + self.conv(base_el) + "}"
        return r"\overset{" + self.conv(over_el) + "}{" + self.conv(base_el) + "}"


_SPACING = r"(?:\s|(?<!\\)\\[,:;! ]|(?<!\\)\\q?quad(?![A-Za-z]))"
_EDGE_SPACING = re.compile(rf"^{_SPACING}+|{_SPACING}+$")


def _tidy(latex: str) -> str:
    """Collapse whitespace and drop spacing commands at either end (never a lone ``\\``)."""
    latex = re.sub(r"[ \t\r\n]+", " ", latex)
    latex = _EDGE_SPACING.sub("", latex)
    trailing = len(latex) - len(latex.rstrip("\\"))
    if trailing % 2:
        latex = latex[:-1]
    return latex.strip()


def math_to_latex(math: ET.Element) -> MathResult:
    """Convert one ``<math>`` element (its presentation branch) to LaTeX; never raises."""
    conv = _Converter()
    try:
        semantics = [c for c in math if local(c.tag) == "semantics"]
        root = semantics[0] if semantics else math
        latex = conv.row(root)
    except Exception:  # noqa: BLE001 - malformed input must become a counted placeholder
        return MathResult(PLACEHOLDER, conv.unavailable + 1)
    return MathResult(_tidy(latex), conv.unavailable)


def mathml_string_to_latex(source: str) -> MathResult:
    """Parse a ``<math>`` XML string and convert it (test and tooling convenience)."""
    try:
        el = ET.fromstring(source)
    except ET.ParseError:
        return MathResult(PLACEHOLDER, 1)
    return math_to_latex(el)
