"""Checks on the real seed bundle in content/compiled/problems.json."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from mathtutor.content.loader import load_bundle
from mathtutor.content.schema import Decimals, Domain, ExpressionAnswer, NumericAnswer

ROOT = Path(__file__).resolve().parents[2]
CONTENT = load_bundle(ROOT / "content" / "compiled" / "problems.json")
PROBLEMS = CONTENT.bundle.problems
TOPICS = [t.topic_id for t in CONTENT.bundle.topics]
EXPR_PROBLEMS = [p for p in PROBLEMS if isinstance(p.answer, ExpressionAnswer)]


def is_all_reals(domain: Domain) -> bool:
    return list(domain.intervals) == [("-inf", "inf", "open", "open")] and not domain.exclude


def test_six_problems_two_per_topic() -> None:
    assert Counter(p.topic for p in PROBLEMS) == {t: 2 for t in TOPICS}


def test_kind_mix() -> None:
    k = Counter(p.answer.kind for p in PROBLEMS)
    assert k["expression"] >= 4 and k["numeric"] >= 1 and k["choice"] >= 1


def test_some_domain_is_not_all_reals() -> None:
    assert any(not is_all_reals(p.answer.domain) for p in EXPR_PROBLEMS)


def test_some_problem_has_misconceptions() -> None:
    assert any(p.misconceptions for p in PROBLEMS)


def test_declared_domains_and_precision_are_pinned() -> None:
    by_id = {p.id: p for p in PROBLEMS}
    for pid, point in [("openstax-c1-3.3-111", "-1"), ("openstax-c1-3.3-115", "0")]:
        answer = by_id[pid].answer
        assert isinstance(answer, ExpressionAnswer), pid
        assert list(answer.domain.intervals) == [("-inf", "inf", "open", "open")], pid
        assert answer.domain.exclude == [point], pid
    numeric = by_id["openstax-c1-3.6-253"].answer
    assert isinstance(numeric, NumericAnswer)
    assert isinstance(numeric.precision, Decimals) and numeric.precision.decimals == 3


def test_urls_match_section() -> None:
    assert all(f"/pages/3-{p.source.section.split('.')[1]}-" in p.source.url for p in PROBLEMS)


def test_transcribed_problems_cite_an_exercise() -> None:
    for p in PROBLEMS:
        if p.answer.kind == "choice":
            assert p.source.adapted and p.source.exercise is None, p.id
        else:
            assert not p.source.adapted and p.source.exercise is not None, p.id


def test_all_human_verified() -> None:
    assert all(p.review.status == "human_verified" for p in PROBLEMS)
