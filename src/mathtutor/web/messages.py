"""Student-facing copy for format issues (rulings R15, R16): plain Calc I/II language."""

from __future__ import annotations

from mathtutor.domain import FormatIssueCode

DEFAULT = {
    FormatIssueCode.EMPTY: "Enter an answer before checking.",
    FormatIssueCode.INCOMPLETE: (
        "Your answer has an empty box or a missing piece. Fill it in and check again."
    ),
    FormatIssueCode.EXACT_REQUIRED: ("Give an exact answer, like 1/3 or √2, instead of a decimal."),
    FormatIssueCode.WRONG_DECIMAL_PLACES: (
        "Round to the number of decimal places the problem asks for, or give an exact answer."
    ),
    FormatIssueCode.INPUT_TOO_LARGE: "That answer is too long to check. Try simplifying it.",
    FormatIssueCode.UNSUPPORTED_NOTATION: (
        "We can't read that notation. Try writing your answer another way."
    ),
}

# Verifier details written for students; shown verbatim (R15).
_VERBATIM_PREFIXES = (
    "Did you mean",
    "Put the function's input in parentheses",
    "Pick one of the listed choices",
    "Give an exact answer",
)

# Technical details from the translator, rewritten for students.
_REWRITES = (
    ("unknown symbol", "Use only the problem's variable, plus constants like π and e."),
    ("mixed number", "Write a mixed number as a fraction, like 7/2 instead of 3½."),
    (
        "number after a factor",
        "Put numbers before letters, like 2x, or use a multiplication sign.",
    ),
)


def format_issue_message(code: FormatIssueCode, detail: str) -> str:
    if detail.startswith(_VERBATIM_PREFIXES):
        return detail
    for prefix, message in _REWRITES:
        if detail.startswith(prefix):
            return message
    return DEFAULT[code]
