"""Which problem comes next (spec 06, "Selection")."""

from __future__ import annotations

from datetime import datetime

from mathtutor.content.loader import LoadedContent, servable
from mathtutor.domain import VerdictStatus

# One entry per presentation: (item_id, latest applied result or None, served_at).
History = list[tuple[str, VerdictStatus | None, datetime]]


def next_item_id(content: LoadedContent, topics: list[str], history: History) -> str | None:
    """The next item in the chosen topics, or ``None`` when every one was answered correctly.

    Candidates are the items never answered correctly, in three tiers:
    1. unseen, in textbook order (topic order, then difficulty, then id);
    2. latest result incorrect, the oldest first;
    3. seen without a usable result (skipped, unable to verify), the oldest first.
    The most recently presented item is skipped while any other candidate remains.
    """
    order = {t.topic_id: t.order for t in content.bundle.topics}
    chosen = set(topics)
    items = sorted(
        (p for p in servable(content) if p.topic in chosen),
        key=lambda p: (order[p.topic], p.difficulty, p.id),
    )

    correct = {item for item, status, _ in history if status is VerdictStatus.CORRECT}
    # Per item: when it was last presented, and its latest result (presentations that ended
    # without a result, such as a skip, do not erase an earlier one).
    latest: dict[str, tuple[datetime, VerdictStatus | None]] = {}
    for item, status, at in sorted(history, key=lambda h: h[2]):
        previous = latest.get(item, (at, None))[1]
        latest[item] = (at, status if status is not None else previous)
    last_presented = max(history, key=lambda h: h[2])[0] if history else None

    unseen = [p.id for p in items if p.id not in latest]
    seen = sorted((latest[p.id][0], p.id) for p in items if p.id in latest and p.id not in correct)
    incorrect = [i for _, i in seen if latest[i][1] is VerdictStatus.INCORRECT]
    other = [i for _, i in seen if latest[i][1] is not VerdictStatus.INCORRECT]

    candidates = unseen + incorrect + other
    preferred = [i for i in candidates if i != last_presented]
    if preferred:
        return preferred[0]
    return candidates[0] if candidates else None
