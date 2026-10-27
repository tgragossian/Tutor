"""Safe HTML for help text: everything escaped; only paragraphs, bold and guard-checked math.

Math is rendered only for the spans the leak guard reads as math (``leak_guard.split_spans``),
so nothing reaches the student as math that the guard did not check. Text the guard cannot
split (unbalanced delimiters, stray LaTeX) is shown as plain escaped text. There are no links,
images or raw HTML: ``[x](u)`` and ``<b>`` stay literal text.
"""

from __future__ import annotations

import html
import re

from mathtutor.help.leak_guard import MalformedMath, split_spans

_HOLE = "\x00"  # stands for a rendered math span while prose is formatted
_HOLE_RE = re.compile(r"\x00(\d+)\x00")
_PROSE_ESCAPE = re.compile(r"\\([$%&#])")
_BOLD = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n\s*")


def _math_field(latex: str) -> str:
    return f"<math-field read-only>{html.escape(latex.strip())}</math-field>"


def render_help_html(text: str) -> str:
    """``text`` as HTML: blank lines become ``<p>``, ``**x**`` ``<strong>``, math spans
    ``<math-field read-only>``; every other character is escaped."""
    text = text.replace(_HOLE, "")
    fields: list[str] = []
    try:
        pieces: list[str] = []
        for kind, content in split_spans(text):
            if kind == "prose":
                pieces.append(html.escape(_PROSE_ESCAPE.sub(r"\1", content)))
            else:
                pieces.append(f"{_HOLE}{len(fields)}{_HOLE}")
                fields.append(_math_field(content))
        body = "".join(pieces)
    except MalformedMath:
        fields = []
        body = html.escape(text)
    paragraphs = []
    for para in _PARAGRAPH_BREAK.split(body.strip()):
        para = para.strip()
        if not para:
            continue
        para = _BOLD.sub(r"<strong>\1</strong>", para).replace("\n", "<br>")
        para = _HOLE_RE.sub(lambda m: fields[int(m.group(1))], para)
        paragraphs.append(f"<p>{para}</p>")
    return "".join(paragraphs)
