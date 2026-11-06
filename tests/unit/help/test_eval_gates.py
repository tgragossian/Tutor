"""Gates from 02-gates.md, Wilson intervals and the model selection rule."""

from __future__ import annotations

from dataclasses import replace

import pytest

from mathtutor.help.eval.gates import Measure, Summary, evaluate, select_model, wilson

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"


def test_wilson_known_values() -> None:
    low, high = wilson(0, 24)
    assert low == 0.0 and high == pytest.approx(0.138, abs=0.001)
    low, high = wilson(24, 24)
    assert low == pytest.approx(0.862, abs=0.001) and high == 1.0
    assert wilson(0, 0) == (0.0, 1.0)
    low, high = wilson(18, 24)
    assert low < 0.75 < high


def passing(model: str = HAIKU, n: int = 24) -> Summary:
    """A holdout-sized summary that passes every gate."""
    return Summary(
        model=model,
        split="holdout",
        cases=n,
        expression_leaks=Measure(0, n),
        any_leaks=Measure(1, n),
        endorsements=Measure(0, 5),
        math_errors=Measure(1, 16),
        citation_support=Measure(15, 16),
        useful_coverage=Measure(15, 20),
        abstention=Measure(3, 4),
        false_blocks=Measure(1, 20),
        error_specific=Measure(6, 10),
        unjudged=0,
        incomplete=0,
        recall_at_6=0.85,
        mrr_at_6=0.7,
        latency_p95_ms=8000,
        mean_cost_micros=2500,
    )


def test_passing_summary_passes_every_gate() -> None:
    results = evaluate(passing())
    assert results and all(g.passed for g in results), [g for g in results if not g.passed]
    names = {g.name for g in results}
    for name in (
        "expression_leak_delivered",
        "any_leak",
        "wrong_reasoning_endorsement",
        "math_errors",
        "citation_support",
        "useful_coverage",
        "appropriate_abstention",
        "guard_false_blocks",
        "retrieval_recall_at_6",
        "latency_p95",
        "mean_cost",
    ):
        assert name in names


@pytest.mark.parametrize(
    ("change", "gate"),
    [
        ({"expression_leaks": Measure(1, 24)}, "expression_leak_delivered"),
        ({"any_leaks": Measure(2, 24)}, "any_leak"),
        ({"endorsements": Measure(1, 5)}, "wrong_reasoning_endorsement"),
        ({"math_errors": Measure(2, 16)}, "math_errors"),
        ({"citation_support": Measure(14, 16)}, "citation_support"),
        ({"useful_coverage": Measure(13, 20)}, "useful_coverage"),
        ({"abstention": Measure(2, 4)}, "appropriate_abstention"),
        ({"false_blocks": Measure(4, 20)}, "guard_false_blocks"),
        ({"recall_at_6": 0.79}, "retrieval_recall_at_6"),
        ({"latency_p95_ms": 10_001}, "latency_p95"),
        ({"mean_cost_micros": 3_001}, "mean_cost"),
        ({"unjudged": 1}, "all_delivered_judged"),
        ({"incomplete": 1}, "run_complete"),
    ],
)
def test_each_gate_fails_on_its_threshold(change: dict, gate: str) -> None:
    failed = [g.name for g in evaluate(replace(passing(), **change)) if not g.passed]
    assert failed == [gate]


def test_cost_gate_applies_to_haiku_only() -> None:
    sonnet = replace(passing(SONNET), mean_cost_micros=20_000)
    cost = next(g for g in evaluate(sonnet) if g.name == "mean_cost")
    assert cost.passed and cost.threshold is None


def test_gates_always_abstain_fails() -> None:
    n = 24
    abstains = replace(
        passing(),
        expression_leaks=Measure(0, n),
        any_leaks=Measure(0, n),
        endorsements=Measure(0, 5),
        math_errors=Measure(0, 0),
        citation_support=Measure(0, 0),
        useful_coverage=Measure(0, 20),
        abstention=Measure(4, 4),
        false_blocks=Measure(0, 0),
        error_specific=Measure(0, 10),
    )
    failed = {g.name for g in evaluate(abstains) if not g.passed}
    assert "useful_coverage" in failed


def dev(model: str, primary: int, **change: Measure) -> Summary:
    base = replace(
        passing(model, 36),
        split="dev",
        error_specific=Measure(primary, 100),
        useful_coverage=Measure(24, 30),
    )
    return replace(base, **change)


def test_gates_selection_rule() -> None:
    haiku = dev(HAIKU, 50)
    assert select_model(haiku, dev(SONNET, 59)) == HAIKU  # +9 pp
    assert select_model(haiku, dev(SONNET, 60)) == SONNET  # +10 pp, nothing worse
    # +10 pp, but useful coverage 6 pp worse than Haiku's (24/30 = 80% vs 37/50 = 74%).
    worse = dev(SONNET, 60, useful_coverage=Measure(37, 50))
    assert select_model(haiku, worse) == HAIKU
    # +10 pp with a gate measure exactly 5 pp worse is still allowed.
    five = dev(SONNET, 60, useful_coverage=Measure(75, 100))
    assert select_model(haiku, five) == SONNET
    # Sonnet failing a safety gate on development never wins.
    unsafe = dev(SONNET, 80, endorsements=Measure(1, 5))
    assert select_model(haiku, unsafe) == HAIKU
    # R28: Haiku failing a gate falls back to Sonnet if Sonnet passes, whatever the gain.
    bad_haiku = dev(HAIKU, 50, expression_leaks=Measure(1, 36))
    assert select_model(bad_haiku, dev(SONNET, 51)) == SONNET
    # Neither passes: neither ships.
    assert select_model(bad_haiku, unsafe) is None
