"""Case and query files: schema, review state, splits grouped by problem, the gate case mix."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from support.evalkit import PROBLEMS, make_case, make_query, mix_cases
from support.helpkit import CONFUSIONS, ROOT

from mathtutor.content.loader import load_bundle
from mathtutor.help.eval.cases import (
    SPLITS,
    check_bank,
    check_grouping,
    check_query_grouping,
    load_cases,
    load_split,
    split_file,
    unreviewed,
)
from mathtutor.help.eval.gates import check_mix

BANK = {
    p.id: p for p in load_bundle(ROOT / "content" / "compiled" / "problems.json").bundle.problems
}
BY_TOPIC: dict[str, list[str]] = {}
for _p in BANK.values():
    BY_TOPIC.setdefault(_p.topic, []).append(_p.id)


def _problems(topics: dict[str, int]) -> list[tuple[str, str]]:
    return [(pid, t) for t, n in topics.items() for pid in sorted(BY_TOPIC[t])[:n]]


def _split_sets() -> tuple[list, list]:
    hold_topics = {t: 3 for t in BY_TOPIC}  # 9 problems, all three topics
    held = {pid for pid, _ in _problems(hold_topics)}
    dev_probs = [(p.id, p.topic) for p in BANK.values() if p.id not in held]
    return mix_cases("dev", dev_probs), mix_cases("holdout", _problems(hold_topics))


def test_splits_grouped_by_problem() -> None:
    dev, hold = _split_sets()
    assert check_grouping(dev, hold, BANK) == []
    # One problem on both sides is refused.
    leaked = [*hold[:-1], make_case(case_id="h-x", split="holdout", problem_id=dev[0].problem_id)]
    assert any("both splits" in e for e in check_grouping(dev, leaked, BANK))
    # A holdout with only two topics or fewer than 7 problems is refused.
    two_topics = [c for c in hold if BANK[c.problem_id].topic != "derivatives.trig"]
    errors = check_grouping(dev, two_topics, BANK)
    assert any("3 topics" in e for e in errors)
    few = [c for c in hold if c.problem_id in {x.problem_id for x in hold[:4]}]
    assert any("problems" in e for e in check_grouping(dev, few, BANK))


def test_case_mix_matches_gates() -> None:
    dev, hold = _split_sets()
    assert check_mix(dev, "dev") == [] and check_mix(hold, "holdout") == []
    # One category short is reported; so is a help type under its minimum share.
    one_short = list(dev)
    one_short.remove(next(c for c in dev if c.category == "nearly_right"))
    assert any("nearly_right" in e for e in check_mix(one_short, "dev"))
    hints_only = [c.model_copy(update={"help_type": "hint", "confusion_id": None}) for c in dev]
    errors = check_mix(hints_only, "dev")
    assert any("feedback" in e for e in errors) and any("explain" in e for e in errors)


def test_case_schema_rules() -> None:
    with pytest.raises(ValidationError):  # explain needs a confusion id
        make_case(help_type="explain", confusion_id=None)
    with pytest.raises(ValidationError):  # exactly one category tag
        make_case(tags=["known_error"])
    with pytest.raises(ValidationError):  # out of scope cases expect an abstention
        make_case(tags=["out_of_scope"], expect_abstain=False)
    with pytest.raises(ValidationError):  # known_error needs an attempt
        make_case(attempts=[])
    with pytest.raises(ValidationError):  # unknown keys are refused
        make_case(answer="18x")
    with pytest.raises(ValidationError):
        make_query(relevant_ids=[])


def test_check_bank_flags_unknown_problem_and_confusion() -> None:
    bad = [
        make_case(case_id="a", problem_id="nope"),
        make_case(
            case_id="b",
            help_type="explain",
            confusion_id="sign_of_cos_derivative",
            tags=["ordinary"],
        ),
    ]
    errors = check_bank(bad, PROBLEMS, CONFUSIONS)
    assert any("nope" in e for e in errors) and any("sign_of_cos_derivative" in e for e in errors)
    assert check_bank([make_case()], PROBLEMS, CONFUSIONS) == []


def test_choice_attempts_must_be_wrong_choice_ids() -> None:
    choice = BANK["adapted-c1-3.6-sinx2"]
    problems = {choice.id: choice}
    good = make_case(problem_id=choice.id, attempts=["b"])
    right = make_case(case_id="r", problem_id=choice.id, attempts=["a"])
    assert check_bank([good], problems, CONFUSIONS) == []
    assert any("correct choice" in e for e in check_bank([right], problems, CONFUSIONS))


def test_query_grouping_by_section() -> None:
    dev = [make_query(query_id=f"d{i}", section="3.6") for i in range(2)]
    hold = [make_query(query_id="h1", split="holdout", section="3.6")]
    assert any("3.6" in e for e in check_query_grouping(dev, hold))
    hold_ok = [make_query(query_id="h1", split="holdout", section="2.3")]
    assert check_query_grouping(dev, hold_ok) == []


def test_unreviewed_lists_needs_review() -> None:
    items = [make_case(), make_case(case_id="dev-002", reviewed_by="needs_review")]
    assert unreviewed(items) == ["dev-002"]
    assert unreviewed([make_query(reviewed_by="someone")]) == ["rq-dev-01"]


def _write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_load_refuses_wrong_split_and_duplicates(tmp_path: Path) -> None:
    row = make_case().model_dump(mode="json")
    path = tmp_path / "dev.jsonl"
    _write(path, [row, row])
    with pytest.raises(ValueError, match="duplicate"):
        load_cases(path, "dev")
    _write(path, [row])
    with pytest.raises(ValueError, match="split"):
        load_cases(path, "holdout")


def test_runner_never_reads_final(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert "final" not in SPLITS
    with pytest.raises(ValueError):
        split_file(tmp_path, "cases", "final")
    for kind in ("cases", "retrieval"):
        for split in ("dev", "holdout", "final"):
            row = (make_case() if kind == "cases" else make_query()).model_dump(mode="json")
            row["split"] = split
            _write(tmp_path / "evals" / "help" / kind / f"{split}.jsonl", [row])
    opened: list[str] = []
    real = Path.read_text

    def spy(self: Path, *args: object, **kwargs: object) -> str:
        opened.append(self.as_posix())
        return real(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", spy)
    for split in SPLITS:
        cases, queries = load_split(tmp_path, split)
        assert {c.split for c in cases} == {split} and {q.split for q in queries} == {split}
    rel = [Path(p).relative_to(tmp_path.as_posix()).as_posix() for p in opened]
    assert rel and not any("final" in p for p in rel)
