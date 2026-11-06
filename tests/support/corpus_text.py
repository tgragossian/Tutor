"""Checks on chunk text: `$` delimiters balance and every `$...$` span holds math."""

import re

# Three plain words in a row (not LaTeX commands) mean prose leaked into a math span.
_PROSE = re.compile(r"(?<![\\A-Za-z])[A-Za-z]{3,} [A-Za-z]{3,} [A-Za-z]{3,}")
_TEXT_CMD = re.compile(r"\\(text|operatorname)\{[^{}]*\}")


def math_spans(text: str) -> list[str] | None:
    """Contents of `$...$`/`$$...$$` spans; None if an unescaped `$` is left unmatched."""
    spans: list[str] = []
    i, start, delim = 0, -1, ""
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "$":
            width = 2 if text.startswith("$$", i) else 1
            if start < 0:
                start, delim = i + width, "$" * width
            elif text.startswith(delim, i):
                spans.append(text[start:i])
                start = -1
                width = len(delim)
            i += width
            continue
        i += 1
    return None if start >= 0 else spans


def prose_in_math(span: str) -> bool:
    return bool(_PROSE.search(_TEXT_CMD.sub(" ", span)))
