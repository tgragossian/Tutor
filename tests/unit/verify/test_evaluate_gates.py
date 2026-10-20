"""Gate B dataset validity (review B-E1, B-E2): provenance, label and category coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mathtutor.verify.evaluate import (
    CATEGORY_MIN,
    GATES_B,
    Metrics,
    dataset_failures,
    gate_failures,
    main,
    parse_cases,
)

ROOT = Path(__file__).resolve().parents[3]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
PROBLEM = "openstax-c1-3.6-221"
GOOD: Any = [
    "InvisibleOperator",
    18,
    "x",
    ["Power", ["Delimiter", ["Add", ["InvisibleOperator", 3, ["Power", "x", 2]], 1]], 2],
]
WRONG: Any = ["InvisibleOperator", 18, "x"]
LABEL_FOR = {"error": "incorrect", "partial": "unsupported", "unsupported": "unsupported"}


def row(i: int, category: str, reviewer: str = "tg") -> dict[str, Any]:
    label = LABEL_FOR.get(category, "correct")
    return {
        "id": f"g-{i:03d}",
        "family": PROBLEM,
        "category": category,
        "problem_id": PROBLEM,
        "answer": {"mathjson": GOOD if label == "correct" else WRONG, "latex": ""},
        "label": label,
        "rationale": "test",
        "reviewer": reviewer,
    }


def full_rows(reviewer: str = "tg") -> list[dict[str, Any]]:
    """Exactly the spec 08 category minimums, every row reviewed."""
    rows: list[dict[str, Any]] = []
    for category, count in CATEGORY_MIN.items():
        rows += [row(len(rows) + i, category, reviewer) for i in range(count)]
    return rows


def failures(rows: list[dict[str, Any]], mode: str = "dev") -> list[str]:
    return dataset_failures(parse_cases(rows), mode)


def test_reviewed_full_coverage_passes() -> None:
    assert failures(full_rows()) == []


@pytest.mark.parametrize("reviewer", ["pending", "generated", "fixture"])
def test_unreviewed_rows_fail_release(reviewer: str) -> None:
    rows = full_rows()
    rows[3]["reviewer"] = reviewer
    assert any("unreviewed" in f and "g-003" in f for f in failures(rows))


def test_blank_reviewer_is_rejected_at_load() -> None:
    rows = full_rows()
    rows[0]["reviewer"] = " "
    with pytest.raises(ValueError, match="reviewer"):
        parse_cases(rows)


def test_draft_skips_only_the_reviewer_check() -> None:
    cases = parse_cases(full_rows("pending"))
    assert dataset_failures(cases, "dev", draft=True) == []
    short = parse_cases(full_rows("pending")[:-1])
    assert dataset_failures(short, "dev", draft=True)


def test_missing_category_fails_release() -> None:
    rows = full_rows()
    del rows[0]["category"]
    assert any("category" in f for f in failures(rows))


def test_unknown_category_fails_release() -> None:
    rows = full_rows()
    rows[0]["category"] = "vibes"
    assert any("vibes" in f for f in failures(rows))


@pytest.mark.parametrize("category", sorted(CATEGORY_MIN))
def test_each_category_minimum_is_enforced(category: str) -> None:
    rows = full_rows()
    drop = next(i for i, r in enumerate(rows) if r["category"] == category)
    del rows[drop]
    assert any(category in f for f in failures(rows))


def test_all_correct_set_fails_release() -> None:
    rows = [row(i, "tricky") for i in range(90)]
    found = failures(rows)
    assert any("incorrect" in f for f in found) and any("unsupported" in f for f in found)


def test_empty_generated_set_fails() -> None:
    assert any("empty" in f for f in failures([], "generated"))


def test_generated_set_needs_no_reviewer_or_category() -> None:
    rows = [row(0, "error", "generated")]
    del rows[0]["category"]
    assert failures(rows, "generated") == []


def test_fa_without_incorrect_cases_is_not_a_pass() -> None:
    m = Metrics(
        fa=(0, 0),
        fr=(0, 80),
        coverage=(80, 80),
        abstain={},
        by_kind_reason_method={},
        agreement=(80, 80),
    )
    assert any("no incorrect" in f for f in gate_failures(m, 80, "dev", GATES_B))
    assert any("no incorrect" in f for f in gate_failures(m, 80, "generated", GATES_B))


def write(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    return path


def run(capsys: pytest.CaptureFixture[str], path: Path, *extra: str) -> tuple[int, str]:
    code = main(["--set", "dev", "--cases", str(path), "--content", str(REAL_PATH), *extra])
    return code, capsys.readouterr().out


def test_cli_pending_dev_set_fails_gate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, write(tmp_path / "p.jsonl", full_rows("pending")), "--gate", "B")
    assert code == 1 and "unreviewed" in out and "gate B: ok" not in out


def test_cli_reviewed_dev_set_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, write(tmp_path / "r.jsonl", full_rows()), "--gate", "B")
    assert code == 0 and "gate B: ok" in out, out


def test_cli_draft_is_labelled_and_never_a_release(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path / "d.jsonl", full_rows("pending"))
    out_json = tmp_path / "d.json"
    code, out = run(capsys, path, "--gate", "B", "--draft", "--out", str(out_json))
    assert code == 0, out
    assert "gate B: ok" not in out and "draft" in out.lower()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["draft"] is True and data["reviewed"] == {"k": 0, "n": len(full_rows())}
