"""Per-user fairness: one user's requests in flight across all items are capped, so a flood
from one user cannot take every help slot."""

from __future__ import annotations

import uuid
from pathlib import Path

from support.helpkit import CFG, TOPIC, WRONG_ANSWER, Kit, make_kit, output

from mathtutor.application.auth import AuthService
from mathtutor.application.practice import ItemView
from mathtutor.help.generator import GenerationRequest
from mathtutor.help.service import HelpIn, HelpOutcome, HelpStatus


def _views(kit: Kit, user: int, sessions: int) -> list[ItemView]:
    """One open item per session; a wrong answer touches a session so the next start is new."""
    ids = []
    for _ in range(sessions):
        sid = kit.practice.start_session(user, [TOPIC])
        view = kit.practice.current_item(user, sid)
        assert isinstance(view, ItemView)
        kit.practice.submit_answer(
            user, sid, uuid.uuid4(), view.session_item_id, view.revision, WRONG_ANSWER
        )
        ids.append(sid)
    out = []
    for sid in ids:
        view = kit.practice.current_item(user, sid)
        assert isinstance(view, ItemView)
        out.append(view)
    return out


def _ask(kit: Kit, user: int, view: ItemView) -> HelpOutcome:
    req = HelpIn(uuid.uuid4(), view.session_item_id, view.revision, "hint", None)
    return kit.svc.request_help(user, req)


def test_one_user_cannot_take_every_slot(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output(), output(), output()])
    cap = CFG.admission.user_in_flight
    assert cap == 2 and CFG.admission.concurrency == 4
    mine = _views(kit, kit.user, 3)
    other = AuthService(kit.sessions, kit.wall).register("other_1", "password-123").user_id
    (theirs,) = _views(kit, other, 1)
    second: list[HelpOutcome] = []
    flood: list[HelpOutcome] = []
    served: list[HelpOutcome] = []
    free_slots: list[int] = []
    calls = 0

    def before(_req: GenerationRequest) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:  # my first request is in flight: a second one, on another item
            second.append(_ask(kit, kit.user, mine[1]))
        elif calls == 2:  # two of mine in flight: the rest of the flood is refused
            for _ in range(5):
                flood.append(_ask(kit, kit.user, mine[2]))
            free_slots.append(kit.svc._slots._value)  # noqa: SLF001
            served.append(_ask(kit, other, theirs))

    kit.generator.before = before
    first = _ask(kit, kit.user, mine[0])
    assert [o.status for o in flood] == [HelpStatus.UNAVAILABLE] * 5
    assert all(o.html is not None and o.sources == [] for o in flood)
    assert first.status is HelpStatus.DELIVERED
    assert [o.status for o in second] == [HelpStatus.DELIVERED]
    assert free_slots == [CFG.admission.concurrency - cap]  # refusals hold no slot
    assert [o.status for o in served] == [HelpStatus.DELIVERED]
    rows = kit.rows()
    assert len(rows) == 3 and len(kit.usage()) == 3  # refused requests reserve nothing
    assert {r.session_item_id for r in rows if r.user_id == kit.user} == {
        mine[0].session_item_id,
        mine[1].session_item_id,
    }


def test_cap_frees_when_a_request_finishes(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output() for _ in range(4)])
    mine = _views(kit, kit.user, 3)
    for view in mine:
        assert _ask(kit, kit.user, view).status is HelpStatus.DELIVERED
