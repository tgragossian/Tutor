"""Turn a help request into a BM25 query (statement first so caps never cut it)."""

from __future__ import annotations

from mathtutor.domain import VerdictStatus
from mathtutor.help.context import HelpContext, HelpType

QUERY_MAX_BYTES = 1200
QUESTION_MAX_BYTES = 500


def _cut(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def build_query(ctx: HelpContext, help_type: HelpType, confusion_text: str | None) -> str:
    parts = [ctx.statement, ctx.topic]
    if help_type == "feedback":
        wrong = [a.latex for a in ctx.attempts if a.status is VerdictStatus.INCORRECT]
        if wrong:
            parts.append(wrong[-1])
    if ctx.misconception_note:
        parts.append(ctx.misconception_note)
    if confusion_text:
        parts.append(_cut(confusion_text, QUESTION_MAX_BYTES))
    query = ""
    for part in parts:
        room = QUERY_MAX_BYTES - len(query.encode("utf-8")) - (1 if query else 0)
        piece = _cut(part, room)
        if piece:
            query = f"{query} {piece}" if query else piece
    return query
