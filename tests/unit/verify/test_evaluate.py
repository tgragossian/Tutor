from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from mathtutor.content.loader import LoadedContent, load_bundle
from mathtutor.domain import Method, VerdictReason, VerdictStatus
from mathtutor.verify import evaluate as ev
from mathtutor.verify.evaluate import (
    GATES_B,
    evaluate,
    gate_failures,
    load_cases,
    main,
    render_summary,
    wilson,
)
from mathtutor.verify.mutate import dump, mutate
from mathtutor.verify.types import CheckRequest, CheckResult, Verdict

ROOT = Path(__file__).resolve().parents[3]
REAL_PATH = ROOT / "content" / "compiled" / "problems.json"
TINY = ROOT / "tests" / "fixtures" / "evals" / "tiny.jsonl"
REAL: LoadedContent = load_bundle(REAL_PATH)
PROBLEM = "openstax-c1-3.6-221"
GOOD: Any = [
    "InvisibleOperator",
    18,
    "x",
    ["Power", ["Delimiter", ["Add", ["InvisibleOperator", 3, ["Power", "x", 2]], 1]], 2],
]


def case(case_id: str, label: str, mathjson: Any, latex: str = "") -> dict[str, Any]:
    return {
        "id": case_id,
        "family": PROBLEM,
        "problem_id": PROBLEM,
        "answer": {"mathjson": mathjson, "latex": latex},
        "label": label,
        "rationale": "test",
        "reviewer": "test",
    }


def write(path: Path, cases: list[dict[str, Any]]) -> Path:
    path.write_text("".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8", newline="\n")
    return path


def run(capsys: pytest.CaptureFixture[str], mode: str, cases: Path, *extra: str) -> tuple[int, str]:
    code = main(["--set", mode, "--cases", str(cases), "--content", str(REAL_PATH), *extra])
    return code, capsys.readouterr().out


def test_wilson_zero_of_n() -> None:
    lo, hi = wilson(0, 100)
    assert lo == 0 and 0.03 < hi < 0.04


def test_wilson_no_data_is_the_whole_interval() -> None:
    assert wilson(0, 0) == (0.0, 1.0)


def test_metrics_denominators() -> None:
    m, _ = evaluate(load_cases(TINY), REAL)
    assert m.fa == (0, 3) and m.fr == (0, 3) and m.coverage == (2, 3)
    assert m.unsupported_accept == (0, 1)


def test_unsupported_label_counts_only_in_abstain() -> None:
    m, results = evaluate(load_cases(TINY), REAL)
    unsupported = next(r for r in results if r.label == "unsupported")
    assert unsupported.status == "format_issue" and unsupported.agrees
    assert m.fa[1] == 3 and m.coverage[1] == 3  # not in FA or coverage denominators
    assert m.abstain["unsupported"] == (0, 1)
    # the correct-labelled placeholder is a format issue: no coverage, never agreement
    assert m.abstain["correct"] == (1, 3)
    placeholder = next(r for r in results if r.id == "t-c3")
    assert not placeholder.agrees


def test_breakdown_by_kind_reason_method() -> None:
    m, _ = evaluate(load_cases(TINY), REAL)
    assert sum(m.by_kind_reason_method.values()) == 7
    assert any(k.startswith("expression|") for k in m.by_kind_reason_method)


def test_gate_fails_on_false_accept(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write(tmp_path / "fa.jsonl", [case("fa-1", "incorrect", GOOD)])  # mislabelled
    code, out = run(capsys, "generated", path, "--gate", "B")
    assert code == 1 and "false accept" in out


def test_gate_fails_on_unsupported_graded_correct(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write(tmp_path / "un.jsonl", [case("un-1", "unsupported", GOOD)])
    m, _ = evaluate(load_cases(path), REAL)
    assert m.unsupported_accept == (1, 1) and m.fa == (0, 0)
    code, out = run(capsys, "generated", path, "--gate", "B")
    assert code == 1 and "unsupported" in out


def test_gate_fails_when_everything_abstains(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unable = Verdict(VerdictStatus.UNABLE_TO_VERIFY, VerdictReason.NOT_PROVEN, Method.NONE)

    def fake(req: CheckRequest, deadline_s: float = 3.0) -> CheckResult:
        return CheckResult(unable, "test")

    monkeypatch.setattr(ev, "check", fake)
    code, out = run(capsys, "dev", TINY, "--gate", "B")
    assert code == 1 and "coverage" in out


def test_gate_fails_under_80_cases(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "dev", TINY, "--gate", "B")
    assert code == 1 and "min_cases" in out


def test_generated_mode_ignores_min_cases(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "generated", TINY, "--gate", "B")
    assert code == 0, out
    assert "min_cases" not in out


def test_gate_failures_dev_checks_fr_and_coverage() -> None:
    m, _ = evaluate(load_cases(TINY), REAL)
    failures = gate_failures(m, 80, "dev", GATES_B)
    assert any("coverage" in f for f in failures)  # 2 of 3 is below 85%


def test_report_formats_zero_as_upper_bound() -> None:
    m, _ = evaluate(load_cases(TINY), REAL)
    object.__setattr__(m, "fa", (0, 120))
    assert "0 of 120 (95% upper bound" in render_summary(m)


def test_results_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "r.json"
    code, _ = run(capsys, "generated", TINY, "--out", str(out))
    assert code == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["verifier_version"].startswith("0.")
    assert len(data["set_sha256"]) == 64
    assert data["metrics"]["fa"]["k"] == 0 and len(data["metrics"]["fa"]["wilson"]) == 2
    assert len(data["cases"]) == 7


def test_missing_dev_set_fails_clearly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(ev, "SET_PATHS", {"dev": tmp_path / "dev.jsonl", "generated": TINY})
    code = main(["--set", "dev", "--content", str(REAL_PATH)])
    assert code == 1 and "dev.jsonl" in capsys.readouterr().out


def test_unknown_problem_is_an_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = case("x-1", "correct", GOOD)
    bad["problem_id"] = "nope"
    code, out = run(capsys, "generated", write(tmp_path / "b.jsonl", [bad]))
    assert code == 1 and "nope" in out


def test_load_cases_rejects_bad_label(tmp_path: Path) -> None:
    path = write(tmp_path / "l.jsonl", [case("l-1", "maybe", GOOD)])
    with pytest.raises(ValueError, match="label"):
        load_cases(path)


def test_load_cases_keeps_decimals_exact(tmp_path: Path) -> None:
    path = write(tmp_path / "d.jsonl", [case("d-1", "correct", 0)])
    raw = path.read_text(encoding="utf-8").replace('"mathjson": 0', '"mathjson": 2.675')
    path.write_text(raw, encoding="utf-8")
    (loaded,) = load_cases(path)
    assert loaded.answer["mathjson"] == {"num": "2.675"}


def test_mutations_deterministic() -> None:
    assert mutate(REAL) == mutate(REAL)


def test_mutations_shape() -> None:
    cases = mutate(REAL)
    assert 20 <= len(cases) <= 60
    assert len({c["id"] for c in cases}) == len(cases)
    assert {c["label"] for c in cases} == {"correct", "incorrect"}
    assert all(c["family"] == c["problem_id"] for c in cases)
    assert all(c["reviewer"] == "generated" for c in cases)


def test_mutations_grade_as_labelled() -> None:
    m, results = evaluate(ev.parse_cases(mutate(REAL)), REAL)
    assert m.fa[0] == 0 and m.fr[0] == 0
    assert not any(r.status == "format_issue" for r in results)


def test_committed_mutations_file_is_current() -> None:
    committed = (ROOT / "evals" / "verifier" / "generated" / "mutations.jsonl").read_bytes()
    assert committed == dump(mutate(REAL))
