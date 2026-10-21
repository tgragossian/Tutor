from datetime import UTC, datetime, timedelta
from pathlib import Path

from mathtutor.application.selection import next_item_id
from mathtutor.content.loader import load_bundle
from mathtutor.domain import VerdictStatus

ROOT = Path(__file__).resolve().parents[3]
CONTENT = load_bundle(ROOT / "content" / "compiled" / "problems.json")
T0 = datetime(2026, 10, 21, tzinfo=UTC)
ALL = ["derivatives.basic_rules", "derivatives.trig", "derivatives.chain_rule"]

# Textbook order: topic order, then difficulty, then id.
ORDER = [
    "openstax-c1-3.3-115",  # basic_rules, difficulty 2
    "openstax-c1-3.3-111",  # basic_rules, difficulty 3
    "adapted-c1-3.5-x2cosx",  # trig, difficulty 2 ("adapted" < "openstax")
    "openstax-c1-3.5-181",  # trig, difficulty 2
    "openstax-c1-3.6-221",  # chain_rule, difficulty 2
    "openstax-c1-3.6-253",  # chain_rule, difficulty 3
]


def t(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_textbook_order_when_unseen() -> None:
    assert next_item_id(CONTENT, ALL, []) == ORDER[0]
    assert next_item_id(CONTENT, ["derivatives.chain_rule"], []) == ORDER[4]
    assert next_item_id(CONTENT, ["derivatives.chain_rule", "derivatives.trig"], []) == ORDER[2]


def test_selection_textbook_order_and_retry_policy() -> None:
    history: list[tuple[str, VerdictStatus | None, datetime]] = [
        (ORDER[0], VerdictStatus.CORRECT, t(0)),
        (ORDER[1], VerdictStatus.INCORRECT, t(1)),
    ]
    topics = ["derivatives.basic_rules", "derivatives.trig"]
    # Unseen first, in textbook order.
    assert next_item_id(CONTENT, topics, history) == ORDER[2]
    history += [
        (ORDER[2], VerdictStatus.INCORRECT, t(2)),
        (ORDER[3], VerdictStatus.INCORRECT, t(3)),
        (ORDER[4], VerdictStatus.CORRECT, t(4)),  # other topic: ignored
    ]
    # Then latest-incorrect, oldest first.
    assert next_item_id(CONTENT, topics, history) == ORDER[1]
    # A later correct answer removes an item for good, whatever came before.
    history.append((ORDER[1], VerdictStatus.CORRECT, t(5)))
    assert next_item_id(CONTENT, topics, history) == ORDER[2]


def test_latest_result_decides() -> None:
    history: list[tuple[str, VerdictStatus | None, datetime]] = [
        (ORDER[0], VerdictStatus.INCORRECT, t(0)),
        (ORDER[0], VerdictStatus.UNABLE_TO_VERIFY, t(5)),
        (ORDER[1], VerdictStatus.INCORRECT, t(1)),
        (ORDER[2], VerdictStatus.INCORRECT, t(9)),
    ]
    topics = ["derivatives.basic_rules"]
    # ORDER[0]'s latest is unable_to_verify: after every latest-incorrect item.
    assert next_item_id(CONTENT, topics, history) == ORDER[1]
    history.append((ORDER[1], VerdictStatus.CORRECT, t(10)))
    assert next_item_id(CONTENT, topics, history) == ORDER[0]


def test_skipped_items_come_back_after_incorrect_ones() -> None:
    history: list[tuple[str, VerdictStatus | None, datetime]] = [
        (ORDER[0], None, t(0)),  # skipped without an answer
        (ORDER[1], VerdictStatus.INCORRECT, t(1)),
        (ORDER[4], VerdictStatus.CORRECT, t(2)),
    ]
    assert next_item_id(CONTENT, ["derivatives.basic_rules"], history) == ORDER[1]


def test_just_presented_item_is_not_repeated_while_others_remain() -> None:
    history: list[tuple[str, VerdictStatus | None, datetime]] = [
        (ORDER[0], None, t(0)),
        (ORDER[1], VerdictStatus.INCORRECT, t(1)),
    ]
    assert next_item_id(CONTENT, ["derivatives.basic_rules"], history) == ORDER[0]
    # Only one candidate left: it repeats.
    history.append((ORDER[0], VerdictStatus.CORRECT, t(2)))
    assert next_item_id(CONTENT, ["derivatives.basic_rules"], history) == ORDER[1]


def test_none_when_all_correct() -> None:
    history = [(i, VerdictStatus.CORRECT, t(n)) for n, i in enumerate(ORDER)]
    assert next_item_id(CONTENT, ALL, history) is None


def test_skip_does_not_erase_an_earlier_incorrect() -> None:
    history: list[tuple[str, VerdictStatus | None, datetime]] = [
        (ORDER[0], VerdictStatus.INCORRECT, t(0)),
        (ORDER[1], VerdictStatus.UNABLE_TO_VERIFY, t(1)),
        (ORDER[0], None, t(2)),  # shown again, skipped
        (ORDER[4], VerdictStatus.CORRECT, t(3)),
    ]
    assert next_item_id(CONTENT, ["derivatives.basic_rules"], history) == ORDER[0]
