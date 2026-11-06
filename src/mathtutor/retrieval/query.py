"""Turn a help request into a BM25 query (statement first so caps never cut it)."""

from __future__ import annotations

from mathtutor.domain import VerdictStatus
from mathtutor.help.config import RetrievalParams
from mathtutor.help.context import HelpContext, HelpType


def _cut(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore")


def build_query(
    ctx: HelpContext, help_type: HelpType, confusion_text: str | None, params: RetrievalParams
) -> str:
    """The query, capped at ``params.query_max_bytes``; the confusion at ``question_max_bytes``."""
    parts = [ctx.statement, ctx.topic]
    if help_type == "feedback":
        # ``ctx.attempts`` is newest first: the latest wrong attempt is the first one (C1-R6).
        latest = next((a.latex for a in ctx.attempts if a.status is VerdictStatus.INCORRECT), None)
        if latest is not None:
            parts.append(latest)
    if ctx.misconception_note:
        parts.append(ctx.misconception_note)
    if confusion_text:
        parts.append(_cut(confusion_text, params.question_max_bytes))
    query = ""
    for part in parts:
        room = params.query_max_bytes - len(query.encode("utf-8")) - (1 if query else 0)
        piece = _cut(part, room)
        if piece:
            query = f"{query} {piece}" if query else piece
    return query
