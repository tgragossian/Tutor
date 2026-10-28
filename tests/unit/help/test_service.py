"""HelpService orchestration (Task 11): scripted generator, fake pools, real SQLite, fake clocks."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from support.helpkit import (
    CFG,
    CORRECT,
    GOOD_TEXT,
    URL,
    Kit,
    chunk,
    make_kit,
    output,
)

from mathtutor.application.errors import Conflict, Forbidden, InvalidAction, InvalidInput, StaleItem
from mathtutor.domain import ItemState
from mathtutor.help import messages
from mathtutor.help.generator import (
    HELP_OUTPUT_SCHEMA,
    HINT_CHOICE_SCHEMA,
    ClaudeGenerator,
    GenerationResult,
    GeneratorError,
)
from mathtutor.help.prompts import START_RULES
from mathtutor.help.render import render_help_html
from mathtutor.help.service import HelpIn, HelpOutcome, HelpService, HelpStatus, SourceRef
from mathtutor.retrieval.corpus import ChunkRole
from mathtutor.store.db import write_transaction
from mathtutor.store.models import User

LICENSE = "CC BY-NC-SA 4.0"


@pytest.fixture
def kit(tmp_path: Path) -> Kit:
    return make_kit(tmp_path)


def test_delivered_hint_with_citation(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.DELIVERED
    assert out.request_id == str(rid)
    assert (out.session_item_id, out.item_revision) == (kit.item.session_item_id, 1)
    assert out.help_seq == 1 and out.hint_level == 1
    assert out.html is not None
    assert "<strong>chain rule</strong>" in out.html
    assert "<math-field read-only>u^3</math-field>" in out.html
    assert out.sources == [SourceRef("Calculus Volume 1, 3.6 The Chain Rule", URL, LICENSE)]
    row = kit.row(rid)
    assert row.status == "delivered" and row.cited_ids == ["c1-3.6-rule1"]
    assert row.calls == 1 and row.hint_level == 1 and row.help_seq == 1
    assert json.loads(row.output_json or "")["text"] == GOOD_TEXT
    assert "c1-3.6-key1" not in row.retrieved_ids  # answer keys are never retrieved
    state = kit.state()
    assert state is not None
    assert (state.hint_level, state.help_seq, state.in_flight) == (2, 1, None)
    (entry,) = kit.usage()
    assert entry.state == "settled" and (entry.input_tokens, entry.output_tokens) == (2000, 300)
    req = kit.generator.requests[0]
    assert "c1-3.6-rule1" in req.user and "<repair>" not in req.user
    assert req.model == CFG.model and 0 < req.timeout_s <= CFG.deadline_s


def test_level_0_before_a_wrong_answer_then_ladder_1_2_3(kit: Kit) -> None:
    """R35: level 0 (how to start) never moves the ladder; after a wrong answer the first hint
    classifies the mistake (all types at level 1), then the same attempt climbs 2 -> 3 -> 3."""
    kit.generator.script = [output() for _ in range(7)]
    assert [kit.help().hint_level for _ in range(3)] == [0, 0, 0]
    starts = [r.user for r in kit.generator.requests]
    assert START_RULES[1] in starts[0] and START_RULES[2] in starts[1]  # two steps,
    assert START_RULES[2] in starts[2]  # then the concrete setup repeats
    assert [r.start_step for r in kit.rows()] == [1, 2, 2]
    state = kit.state()
    assert state is not None and (state.hint_counts, state.hint_attempt_pk) == ({}, None)
    assert state.start_hints == 3
    kit.submit_wrong()
    assert [kit.help().hint_level for _ in range(4)] == [1, 2, 3, 3]
    reqs = kit.generator.requests[3:]
    assert [r.schema == HINT_CHOICE_SCHEMA for r in reqs] == [True, False, False, False]
    assert "Level 2" in reqs[1].user and "Level 3" in reqs[2].user
    state = kit.state()
    assert state is not None and state.help_seq == 7
    assert (state.hint_type, state.hint_counts, state.hint_level) == (
        "rule_misapplied",
        {"rule_misapplied": 4},
        3,
    )


def test_feedback_and_explain_do_not_advance_ladder(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output(), output()]
    assert kit.help("feedback").status is HelpStatus.DELIVERED
    out = kit.help("explain", "why_multiply_inside")
    assert out.status is HelpStatus.DELIVERED and out.hint_level is None
    state = kit.state()
    assert state is not None and (state.hint_level, state.help_seq) == (1, 2)


def test_feedback_requires_wrong_attempt(kit: Kit) -> None:
    with pytest.raises(InvalidAction) as info:
        kit.help("feedback")
    assert info.value.code == "no_wrong_attempt"
    assert kit.rows() == [] and kit.usage() == []
    kit.submit_wrong()
    kit.generator.script = [output()]
    assert kit.help("feedback").status is HelpStatus.DELIVERED


def test_explain_requires_known_confusion(kit: Kit) -> None:
    for bad in (None, "nope_not_listed", "power_rule_why"):  # last: another topic's id
        with pytest.raises(InvalidInput):
            kit.help("explain", bad)
    with pytest.raises(InvalidInput):
        kit.help("hint", "why_multiply_inside")
    assert kit.rows() == []
    kit.generator.script = [output()]
    assert kit.help("explain", "why_multiply_inside").status is HelpStatus.DELIVERED
    assert "Why do I multiply by the derivative of the inside?" in kit.generator.requests[0].user


def test_unknown_help_type_rejected(kit: Kit) -> None:
    with pytest.raises(InvalidInput):
        kit.help("question")  # type: ignore[arg-type]


def test_unknown_citation_repairs_then_fallback(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output(ids=("nope",)), output(ids=("c1-3.6-key1",))]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.FALLBACK
    assert out.html == render_help_html(messages.NUDGE.format(section="Section 3.6"))
    assert out.sources == [SourceRef("Calculus Volume 1, 3.6 The Chain Rule", URL, LICENSE)]
    first, second = kit.generator.requests
    assert "<repair>" not in first.user and "<repair>" in second.user
    assert out.hint_level == 1
    state = kit.state()
    assert state is not None and state.hint_level == 1 and state.help_seq == 1
    assert [e.call_no for e in kit.usage()] == [1, 2]
    assert all(e.state == "settled" for e in kit.usage())
    assert kit.row(rid).calls == 2 and kit.row(rid).reason == "invalid_citation"


def test_unknown_citation_repaired_on_second_call(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output(ids=("nope",)), output()]
    out = kit.help()
    assert out.status is HelpStatus.DELIVERED and out.hint_level == 1
    assert kit.state().hint_level == 2  # type: ignore[union-attr]


def test_leak_repairs_then_fallback(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output(), output()], guard_verdict=CORRECT)
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.FALLBACK
    assert GOOD_TEXT not in (out.html or "") and "u^3" not in (out.html or "")
    assert len(kit.generator.requests) == 2 and kit.guard_pool.requests
    row = kit.row(rid)
    assert row.reason == "invalid_guard_leak" and json.loads(row.output_json or "")["text"]
    assert row.guard_counts["leak"] == 2
    assert kit.state().hint_level == 1  # type: ignore[union-attr]


def test_refusal_counts_as_invalid(kit: Kit) -> None:
    refusal = GenerationResult(None, "refusal", 1500, 5, CFG.model, None, 9)
    cut = GenerationResult(None, "max_tokens", 1500, 1000, CFG.model, None, 9)
    kit.generator.script = [refusal, cut]
    out = kit.help()
    assert out.status is HelpStatus.FALLBACK and len(kit.generator.requests) == 2
    assert [(e.state, e.output_tokens) for e in kit.usage()] == [("settled", 5), ("settled", 1000)]


def test_at_most_two_calls(kit: Kit) -> None:
    bad = GenerationResult("not json", "end_turn", 100, 10, CFG.model, None, 5)
    kit.generator.script = [bad, bad, bad]
    out = kit.help()
    assert out.status is HelpStatus.FALLBACK
    assert len(kit.generator.requests) == 2 and len(kit.generator.script) == 1
    assert len(kit.usage()) == 2


def test_abstain_ignores_text_and_ids(kit: Kit) -> None:
    kit.generator.script = [output("Sneaky $18x$", ("c1-3.6-rule1",), abstain=True)]
    out = kit.help()
    assert out.status is HelpStatus.ABSTAINED
    assert out.html == render_help_html(messages.ABSTAIN) and out.sources == []
    assert kit.state().hint_level == 1  # type: ignore[union-attr]
    assert "18x" not in (kit.rows()[0].output_json or "")


@pytest.mark.parametrize("kind", ["timeout", "connection"])
def test_timeout_marks_uncertain_no_resend(kit: Kit, kind: str) -> None:
    kit.generator.script = [GeneratorError(kind, billed_unknown=True), output()]  # type: ignore[arg-type]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.UNAVAILABLE
    assert out.html == render_help_html(messages.UNAVAILABLE)
    assert len(kit.generator.requests) == 1 and len(kit.generator.script) == 1
    (entry,) = kit.usage()
    assert entry.state == "uncertain"
    assert kit.row(rid).reason == f"generator_{kind}"
    state = kit.state()
    assert state is not None and state.in_flight is None and state.hint_level == 1


def test_gateway_timeout_is_uncertain(kit: Kit) -> None:
    kit.generator.script = [GeneratorError("api_error", status_code=504)]
    assert kit.help().status is HelpStatus.UNAVAILABLE
    assert kit.usage()[0].state == "uncertain"


def test_rate_limited_error_settles_at_zero(kit: Kit) -> None:
    kit.generator.script = [GeneratorError("rate_limited", status_code=429)]
    assert kit.help().status is HelpStatus.UNAVAILABLE
    (entry,) = kit.usage()
    assert entry.state == "settled" and entry.settled_micros == 0


def _crash(_req: object) -> None:
    raise RuntimeError("unexpected")


def test_unexpected_generator_crash_keeps_reservation_uncertain(kit: Kit) -> None:
    """Review C1-R3: once dispatched, an unknown failure never releases the reservation."""
    kit.generator.before = _crash
    assert kit.help().status is HelpStatus.UNAVAILABLE
    (entry,) = kit.usage()
    assert entry.state == "uncertain"


def test_reply_decode_error_retains_spend_reservation(kit: Kit) -> None:
    sent: list[dict[str, object]] = []

    def create(**kwargs: object) -> SimpleNamespace:
        sent.append(kwargs)
        return SimpleNamespace(stop_reason="end_turn", content=None)  # served, unreadable

    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    kit.svc._pipeline._generator = ClaudeGenerator(  # noqa: SLF001
        "offline-test-key", client_factory=lambda **_: client, clock=kit.clock
    )
    assert kit.help().status is HelpStatus.UNAVAILABLE
    assert len(sent) == 1
    (entry,) = kit.usage()
    assert entry.state == "uncertain", (entry.state, entry.settled_micros)


def test_repair_call_crash_keeps_only_that_call_uncertain(kit: Kit) -> None:
    kit.generator.script = [output(ids=("nope",)), output()]
    calls = 0

    def crash_second(_req: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("unexpected")

    kit.generator.before = crash_second
    assert kit.help().status is HelpStatus.UNAVAILABLE
    first, second = kit.usage()
    assert first.state == "settled" and first.settled_micros > 0
    assert second.state == "uncertain"


def test_prompt_budget_failure_before_dispatch_settles_zero(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, cfg=CFG.model_copy(update={"max_input_tokens": 10}))
    out = kit.help()
    assert out.status is HelpStatus.UNAVAILABLE
    assert kit.generator.requests == []
    (entry,) = kit.usage()
    assert entry.state == "settled" and entry.settled_micros == 0


def test_no_hits_abstains_without_call(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()], chunks=[chunk("c1-9.9-z", "zebra quokka walrus")])
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.ABSTAINED and kit.generator.requests == []
    (entry,) = kit.usage()
    assert entry.state == "settled" and entry.settled_micros == 0
    assert kit.row(rid).calls == 0 and kit.row(rid).reason == "no_hits"


def test_hit_containing_answer_dropped(tmp_path: Path) -> None:
    leaky = chunk("c1-3.6-leak", "By the chain rule the derivative is 18 x ( 3x^2 + 1 )^2 .")
    choice_safe = chunk("c1-3.6-rule1", "The chain rule multiplies by the inner derivative.")
    kit = make_kit(tmp_path, [output()], chunks=[leaky, choice_safe])
    rid = uuid.uuid4()
    assert kit.help(rid=rid).status is HelpStatus.DELIVERED
    assert kit.row(rid).retrieved_ids == ["c1-3.6-rule1"]
    assert "c1-3.6-leak" not in kit.generator.requests[0].user
    assert "18 x" not in kit.generator.requests[0].user


def test_only_answer_hits_abstain(tmp_path: Path) -> None:
    leaky = chunk("c1-3.6-leak", "Chain rule result: 18x(3x^2+1)^2", role=ChunkRole.EXAMPLE)
    kit = make_kit(tmp_path, [output()], chunks=[leaky])
    assert kit.help().status is HelpStatus.ABSTAINED and kit.generator.requests == []


def test_same_id_replays(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    first = kit.help(rid=rid)
    again = kit.help(rid=rid)
    assert again == first
    assert len(kit.generator.requests) == 1 and len(kit.usage()) == 1 and len(kit.rows()) == 1
    assert kit.state().hint_level == 2  # type: ignore[union-attr]


def test_replay_after_presentation_changed_is_stale(kit: Kit) -> None:
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    kit.help(rid=rid)
    kit.submit_wrong()
    replay = kit.help(rid=rid, revision=0)
    assert replay.status is HelpStatus.STALE and replay.html is None


def test_same_id_different_payload_conflicts(kit: Kit) -> None:
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    kit.help(rid=rid)
    kit.submit_wrong()
    with pytest.raises(Conflict):
        kit.help("feedback", rid=rid)
    with pytest.raises(Conflict):
        kit.help(rid=rid)  # same type, different revision


def test_other_users_item_forbidden(kit: Kit) -> None:
    with pytest.raises(Forbidden):
        kit.help(user=kit.user + 99)


def test_wrong_revision_is_stale_item(kit: Kit) -> None:
    with pytest.raises(StaleItem):
        kit.help(revision=5)


def test_help_closed_after_reveal(kit: Kit) -> None:
    for _ in range(3):
        kit.submit_wrong()
    assert kit.item.state is ItemState.EXHAUSTED
    kit.generator.script = [output()]
    assert kit.help().status is HelpStatus.DELIVERED  # exhausted still has help
    kit.practice.reveal(kit.user, kit.session_id, kit.item.session_item_id, kit.item.revision)
    kit.refresh()
    with pytest.raises(InvalidAction):
        kit.help()


def test_help_never_changes_tries_or_revision(kit: Kit) -> None:
    kit.submit_wrong()
    before = kit.db_item()
    kit.generator.script = [output(), output(), output(ids=("x",)), output(ids=("x",))]
    kit.help()
    kit.help("feedback")
    kit.help()
    after = kit.db_item()
    assert (after.revision, after.tries_used, after.state) == (
        before.revision,
        before.tries_used,
        before.state,
    )


def test_pending_while_in_flight(kit: Kit) -> None:
    """A second request on the item while the first is inside its provider call."""
    first, other, same = uuid.uuid4(), uuid.uuid4(), []
    inner: list[HelpOutcome] = []

    def nested(_req: object) -> None:
        kit.generator.before = None
        inner.append(kit.help(rid=other))
        same.append(kit.help(rid=first))  # the in-flight id itself: pending too

    kit.generator.script = [output()]
    kit.generator.before = nested
    assert kit.help(rid=first).status is HelpStatus.DELIVERED
    (pending,) = inner
    assert pending.status is HelpStatus.PENDING and pending.html is None
    assert pending.request_id == str(first)  # names the request that is in flight
    assert same[0].status is HelpStatus.PENDING
    assert len(kit.usage()) == 1 and len(kit.generator.requests) == 1 and len(kit.rows()) == 1


def test_abandoned_in_flight_is_recovered(kit: Kit) -> None:
    """A request stuck in flight past ``uncertain_after_s`` (a crashed worker) no longer
    blocks the item; if it ever finishes, it finalizes as stale."""
    old, new = uuid.uuid4(), uuid.uuid4()
    inner: list[HelpOutcome] = []

    def stuck(_req: object) -> None:
        kit.generator.before = None
        kit.wall.advance(seconds=CFG.admission.uncertain_after_s + 1)
        inner.append(kit.help(rid=new))

    kit.submit_wrong()
    kit.generator.script = [output(), output()]
    kit.generator.before = stuck
    outer = kit.help(rid=old)
    (newer,) = inner
    assert newer.status is HelpStatus.DELIVERED
    assert outer.status is HelpStatus.STALE and outer.html is None
    row = kit.row(old)
    assert row.status == "unavailable" and row.reason == "abandoned" and row.output_json is None
    state = kit.state()
    assert state is not None and (state.hint_level, state.help_seq, state.in_flight) == (2, 1, None)


def test_semaphore_exhausted_is_unavailable(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()])
    held = [kit.svc._slots.acquire(blocking=False) for _ in range(CFG.admission.concurrency)]
    assert all(held)
    out = kit.help()
    assert out.status is HelpStatus.UNAVAILABLE and kit.rows() == [] and kit.usage() == []
    kit.svc._slots.release()
    assert kit.help().status is HelpStatus.DELIVERED


def test_limited_by_ledger(kit: Kit) -> None:
    kit.generator.script = [output() for _ in range(CFG.admission.per_hour)]
    for _ in range(CFG.admission.per_hour):
        assert kit.help().status is HelpStatus.DELIVERED
    out = kit.help()
    assert out.status is HelpStatus.LIMITED and out.html == render_help_html(messages.LIMITED)
    assert len(kit.rows()) == CFG.admission.per_hour


def test_second_call_over_budget_falls_back(kit: Kit) -> None:
    kit.generator.script = [output(ids=("nope",)), output()]
    real = kit.ledger.reserve_call

    def refuse(*a: object, **k: object) -> int:
        from mathtutor.application.errors import HelpLimited

        raise HelpLimited("budget")

    kit.ledger.reserve_call = refuse  # type: ignore[method-assign]
    out = kit.help()
    kit.ledger.reserve_call = real  # type: ignore[method-assign]
    assert out.status is HelpStatus.FALLBACK and len(kit.generator.requests) == 1


def test_deadline_spent_during_call_falls_back(kit: Kit) -> None:
    def slow(_req: object) -> None:
        kit.clock.t += CFG.deadline_s + 1

    kit.generator.script = [output(), output()]
    kit.generator.before = slow
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    assert out.status is HelpStatus.FALLBACK and len(kit.generator.requests) == 1
    assert kit.row(rid).reason == "deadline" and kit.guard_pool.requests == []


def test_deadline_spent_before_call_is_unavailable(kit: Kit) -> None:
    kit.generator.script = [output()]
    real = kit.svc._build_context

    def slow(*a: object, **k: object) -> object:
        kit.clock.t += CFG.deadline_s + 1
        return real(*a, **k)  # type: ignore[arg-type]

    kit.svc._build_context = slow  # type: ignore[method-assign]
    assert kit.help().status is HelpStatus.UNAVAILABLE and kit.generator.requests == []
    assert kit.usage()[0].settled_micros == 0


def test_context_failure_is_unavailable_and_clears_in_flight(kit: Kit) -> None:
    def boom(*a: object, **k: object) -> object:
        raise RuntimeError("secret student text")

    kit.svc._build_context = boom  # type: ignore[method-assign]
    assert kit.help().status is HelpStatus.UNAVAILABLE
    assert kit.state().in_flight is None  # type: ignore[union-attr]


def test_disabled_service_is_unavailable(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()])
    svc = HelpService(
        kit.sessions,
        CFG,
        kit.ledger,
        kit.svc._pipeline,
        kit.grade_pool,
        {},
        clock=kit.clock,
        now=kit.wall,
        enabled=False,
    )
    assert not svc.enabled
    req = HelpIn(uuid.uuid4(), kit.item.session_item_id, 0, "hint", None)
    assert svc.request_help(kit.user, req).status is HelpStatus.UNAVAILABLE
    assert kit.rows() == []


def test_availability(kit: Kit) -> None:
    av = kit.svc.availability(kit.item, kit.user)
    assert av.enabled and av.types == ["hint", "explain"] and av.hint_level == 0
    assert [c.id for c in av.confusions][0] == "why_multiply_inside"
    kit.submit_wrong()
    after = kit.svc.availability(kit.item, kit.user)
    assert after.types == ["hint", "feedback", "explain"] and after.hint_level == 1
    with pytest.raises(Forbidden):
        kit.svc.availability(kit.item, kit.user + 99)


def test_logs_hold_no_text(kit: Kit, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    kit.submit_wrong()
    kit.generator.script = [output("Secret $u^7$ words"), output(ids=("nope",))]
    kit.help("feedback")
    kit.generator.script = [GeneratorError("timeout", billed_unknown=True)]
    kit.help()
    logged = caplog.text
    for secret in ("Secret", "u^7", "chain rule", "2x", "derivative", "inner"):
        assert secret not in logged


def test_epoch_recorded_at_admission(kit: Kit) -> None:
    with write_transaction(kit.sessions) as db:
        user = db.get(User, kit.user)
        assert user is not None
        user.privacy_epoch = 4
    kit.generator.script = [output()]
    rid = uuid.uuid4()
    assert kit.help(rid=rid).status is HelpStatus.DELIVERED
    assert kit.row(rid).privacy_epoch == 4


# -- ruling R35: a hint ladder per mistake type -------------------------------------------------


def _typed(mistake_type: str | None) -> GenerationResult:
    body: dict[str, object] = {"text": GOOD_TEXT, "source_ids": ["c1-3.6-rule1"], "abstain": False}
    if mistake_type is not None:
        body["mistake_type"] = mistake_type
    return GenerationResult(json.dumps(body), "end_turn", 2000, 300, CFG.model, "req_x", 12)


def _two_hints_on(kit: Kit, mistake_type: str) -> None:
    """A wrong answer classified as ``mistake_type``, then a second hint on it."""
    kit.submit_wrong()
    kit.generator.script = [_typed(mistake_type), output()]
    assert [kit.help().hint_level for _ in range(2)] == [1, 2]


def test_classifying_prompt_offers_each_type_its_level(kit: Kit) -> None:
    _two_hints_on(kit, "algebra")  # algebra has had 2 hints: next is level 3
    kit.submit_wrong()
    kit.generator.script = [_typed("wrong_rule")]
    rid = uuid.uuid4()
    out = kit.help(rid=rid)
    req = kit.generator.requests[-1]
    assert req.schema == HINT_CHOICE_SCHEMA
    assert "`algebra` (an arithmetic, sign or simplifying slip): Level 3" in req.user
    assert "`wrong_rule` (picked the wrong rule or method): Level 1" in req.user
    assert "- Level 1:" in req.user and "- Level 3:" in req.user and "- Level 2:" not in req.user
    assert out.status is HelpStatus.DELIVERED and out.hint_level == 1  # wrong_rule's level
    row = kit.row(rid)
    assert (row.hint_level, row.mistake_type) == (1, "wrong_rule")
    state = kit.state()
    assert state is not None
    assert state.hint_counts == {"algebra": 2, "wrong_rule": 1} and state.hint_type == "wrong_rule"


def test_same_type_on_a_new_attempt_keeps_climbing(kit: Kit) -> None:
    _two_hints_on(kit, "algebra")
    kit.submit_wrong()
    kit.generator.script = [_typed("algebra")]
    assert kit.help().hint_level == 3


def test_returning_to_an_earlier_type_resumes_its_level(kit: Kit) -> None:
    _two_hints_on(kit, "algebra")  # algebra: 2 hints
    kit.submit_wrong()
    kit.generator.script = [_typed("incomplete")]
    assert kit.help().hint_level == 1  # a new type starts at 1
    kit.submit_wrong()
    kit.generator.script = [_typed("algebra")]
    assert kit.help().hint_level == 3  # back to algebra: its third hint


def test_classifying_reply_without_a_type_is_repaired(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.default_mistake_type = None
    kit.generator.script = [_typed(None), _typed("incomplete")]
    out = kit.help()
    assert out.status is HelpStatus.DELIVERED and out.hint_level == 1
    assert len(kit.generator.requests) == 2  # invalid, then the repair call
    state = kit.state()
    assert state is not None and state.hint_counts == {"incomplete": 1}


def test_undelivered_classifying_hint_leaves_the_ladder(kit: Kit) -> None:
    _two_hints_on(kit, "algebra")
    before = kit.state()
    assert before is not None
    kit.submit_wrong()
    kit.generator.script = [GeneratorError("rate_limited", status_code=429)]
    assert kit.help().status is HelpStatus.UNAVAILABLE
    after = kit.state()
    assert after is not None
    assert (after.hint_counts, after.hint_attempt_pk) == (
        before.hint_counts,
        before.hint_attempt_pk,
    )


def test_feedback_never_classifies_or_counts(kit: Kit) -> None:
    kit.submit_wrong()
    kit.generator.script = [output()]
    assert kit.help("feedback").status is HelpStatus.DELIVERED
    assert kit.generator.requests[-1].schema == HELP_OUTPUT_SCHEMA
    state = kit.state()
    assert state is not None and state.hint_counts == {}
