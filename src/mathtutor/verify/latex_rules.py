"""Reject-only rules read off the submitted LaTeX (R22). Grading never uses LaTeX."""

from __future__ import annotations

FUNCTION_PARENS_DETAIL = "Put the function's input in parentheses, like sin(x)."

_FUNCTIONS = frozenset({"sin", "cos", "tan", "sec", "csc", "cot", "ln", "log", "lg", "lb", "exp"})
_THIN_SPACES = frozenset({",", ";", "!", " "})
_ABS_COMMANDS = ("lvert", "vert")


def _command_at(tex: str, i: int) -> str:
    """The letters of the command whose backslash is at ``i`` ('' for a symbol command)."""
    j = i + 1
    while j < len(tex) and tex[j].isascii() and tex[j].isalpha():
        j += 1
    return tex[i + 1 : j]


def _skip_token(tex: str, i: int) -> int:
    """Index after one braced group or one token starting at ``i``."""
    if i >= len(tex):
        return i
    if tex[i] == "{":
        depth = 0
        while i < len(tex):
            if tex[i] == "\\":
                i += 2
                continue
            depth += tex[i] == "{"
            depth -= tex[i] == "}"
            i += 1
            if depth == 0:
                break
        return min(i, len(tex))
    if tex[i] == "\\":
        return i + 1 + max(len(_command_at(tex, i)), 1)
    return i + 1


def _skip_blanks(tex: str, i: int) -> int:
    while i < len(tex):
        if tex[i].isspace():
            i += 1
        elif tex[i] == "\\" and i + 1 < len(tex) and tex[i + 1] in _THIN_SPACES:
            i += 2
        else:
            break
    return i


def _has_opener(tex: str, i: int) -> bool:
    if i >= len(tex):
        return False
    if tex[i] in "(|":
        return True
    if tex[i] != "\\":
        return False
    name = _command_at(tex, i)
    if name in _ABS_COMMANDS:
        return True
    if name != "left":
        return False
    j = _skip_blanks(tex, i + 1 + len(name))
    if j < len(tex) and tex[j] in "(|":
        return True
    return j < len(tex) and tex[j] == "\\" and _command_at(tex, j) in _ABS_COMMANDS


def _wrapped_function(tex: str, end: int) -> tuple[str, int] | None:
    """The ``{NAME}`` group at ``end`` after ``\\operatorname``/``\\mathrm``: (NAME, index after)."""
    start = _skip_blanks(tex, end)
    if start >= len(tex) or tex[start] != "{":
        return None
    after = _skip_token(tex, start)
    inner = tex[start + 1 : after - 1].strip()
    # MathLive writes a typed ``\\operatorname{sin}`` back as ``\\operatorname{\\mathrm{sin}}``.
    if inner.startswith("\\mathrm{") and inner.endswith("}"):
        inner = inner[len("\\mathrm{") : -1].strip()
    return (inner, after) if inner in _FUNCTIONS else None


def unparenthesized_function(latex: str) -> str | None:
    """The first function (e.g. ``\\sin``) whose input is not parenthesized, or None."""
    i = 0
    while i < len(latex):
        if latex[i] != "\\":
            i += 1
            continue
        name = _command_at(latex, i)
        end = i + 1 + max(len(name), 1)  # a symbol command such as ``\\\\`` spans two characters
        label = "\\" + name
        if name in ("operatorname", "mathrm"):
            wrapped = _wrapped_function(latex, end)
            if wrapped is not None:
                label, end = f"\\{name}{{{wrapped[0]}}}", wrapped[1]
                name = wrapped[0]
        if name in _FUNCTIONS:
            j = _skip_blanks(latex, end)
            while j < len(latex) and latex[j] in "^_":
                j = _skip_blanks(latex, _skip_token(latex, _skip_blanks(latex, j + 1)))
            if not _has_opener(latex, j):
                return label
        i = end
    return None
