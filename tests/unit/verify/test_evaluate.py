from __future__ import annotations

import json
from collections.abc import Callable
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


def test_wrong_decimal_places_agrees_with_unsupported(tmp_path: Path) -> None:
    """R24: -0.5830 on problem 253 (3 places requested) is a format issue, not a verdict."""
    row = {
        **case("r24-1", "unsupported", ["Negate", {"num": "0.583"}], "-0.5830"),
        "family": "openstax-c1-3.6-253",
        "problem_id": "openstax-c1-3.6-253",
    }
    _, results = evaluate(load_cases(write(tmp_path / "r24.jsonl", [row])), REAL)
    assert results[0].status == "format_issue" and results[0].agrees


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


def abstaining(reason: VerdictReason) -> Callable[[CheckRequest], CheckResult]:
    unable = Verdict(VerdictStatus.UNABLE_TO_VERIFY, reason, Method.NONE)
    return lambda req: CheckResult(unable, "test")


def test_gate_fails_when_everything_abstains() -> None:
    m, _ = evaluate(load_cases(TINY), REAL, grade=abstaining(VerdictReason.NOT_PROVEN))
    failures = gate_failures(m, 80, "dev", GATES_B)
    assert any("coverage" in f for f in failures)


def test_gate_fails_under_80_cases(capsys: pytest.CaptureFixture[str]) -> None:
    code, out = run(capsys, "dev", TINY, "--gate", "B")
    assert code == 1 and "min_cases" in out


def test_generated_mode_ignores_min_cases(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agreeing = [c for c in load_rows(TINY) if c["id"] != "t-c3"]
    code, out = run(capsys, "generated", write(tmp_path / "ok.jsonl", agreeing), "--gate", "B")
    assert code == 0, out
    assert "min_cases" not in out


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("reason", [VerdictReason.NOT_PROVEN, VerdictReason.INTERNAL_ERROR])
@pytest.mark.parametrize("mode", ["generated", "dev"])
def test_gate_fails_when_verifier_abstains_or_crashes(mode: str, reason: VerdictReason) -> None:
    m, _ = evaluate(load_cases(TINY), REAL, grade=abstaining(reason))
    assert gate_failures(m, 80, mode, GATES_B)


def test_generated_gate_fails_on_any_disagreement() -> None:
    m, _ = evaluate(load_cases(TINY), REAL)  # t-c3 (a placeholder labelled correct) disagrees
    assert any("regression" in f for f in gate_failures(m, 7, "generated", GATES_B))


def test_internal_error_is_counted_and_fails_gate() -> None:
    m, _ = evaluate(load_cases(TINY), REAL, grade=abstaining(VerdictReason.INTERNAL_ERROR))
    assert m.internal_errors == 7
    for mode in ("dev", "generated"):
        assert any("internal_error" in f for f in gate_failures(m, 80, mode, GATES_B))


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


@pytest.mark.parametrize(
    "mutation",
    [
        {"inline_spce": {}},
        {"rationale": ""},
        {"reviewer": "  "},
        {"answer": {"mathjsn": 1}},
        {"extra": 1},
    ],
)
def test_case_rows_are_strict(tmp_path: Path, mutation: dict[str, Any]) -> None:
    row = {**case("s-1", "correct", GOOD), **mutation}
    with pytest.raises(ValueError, match="s-1"):
        load_cases(write(tmp_path / "s.jsonl", [row]))


def test_missing_rationale_is_rejected(tmp_path: Path) -> None:
    row = case("s-2", "correct", GOOD)
    del row["reviewer"]
    with pytest.raises(ValueError, match="s-2"):
        load_cases(write(tmp_path / "s.jsonl", [row]))


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
    # Several mutations per problem in the bundle (22 problems after task 15).
    assert 20 <= len(cases) <= 8 * len({c["problem_id"] for c in cases})
    assert len({c["id"] for c in cases}) == len(cases)
    assert {c["label"] for c in cases} == {"correct", "incorrect"}
    assert all(c["family"] == c["problem_id"] for c in cases)
    assert all(c["reviewer"] == "generated" for c in cases)


def test_mutations_grade_as_labelled() -> None:
    m, results = evaluate(ev.parse_cases(mutate(REAL)), REAL)
    assert m.fa[0] == 0 and m.fr[0] == 0
    assert all(r.agrees for r in results)


def test_committed_mutations_file_is_current() -> None:
    committed = (ROOT / "evals" / "verifier" / "generated" / "mutations.jsonl").read_bytes()
    assert committed == dump(mutate(REAL))


def test_case_rows_keep_raw_inputs(tmp_path: Path) -> None:
    typed = {**case("r-1", "correct", GOOD), "raw_latex": "18x(3x^2+1)^2"}
    keyed = {**case("r-2", "unsupported", "x", "x^{}"), "raw_keys": ["x", "^"]}
    loaded = load_cases(write(tmp_path / "r.jsonl", [typed, keyed]))
    assert loaded[0].raw_latex == "18x(3x^2+1)^2" and loaded[0].raw_keys is None
    assert loaded[1].raw_keys == ["x", "^"] and loaded[1].raw_latex is None


def test_unsupported_label_agrees_with_partial_input(tmp_path: Path) -> None:
    rows = [
        case("p-1", "unsupported", "x", "x^{}"),  # incomplete
        case("p-2", "unsupported", "Nothing"),  # empty
    ]
    m, results = evaluate(load_cases(write(tmp_path / "p.jsonl", rows)), REAL)
    assert [r.reason for r in results] == ["format:incomplete", "format:empty"]
    assert all(r.agrees for r in results) and m.agreement == (2, 2)


def test_dev_set_lives_under_human() -> None:
    assert ev.SET_PATHS["dev"] == Path("evals/verifier/human/dev.jsonl")


def test_committed_dev_set_loads_sorted_with_raw_inputs() -> None:
    path = ROOT / ev.SET_PATHS["dev"]
    raw = path.read_bytes()
    assert b"\r" not in raw
    cases = load_cases(path)
    assert len(cases) >= 80
    assert [c.id for c in cases] == sorted(c.id for c in cases)
    typed = [c for c in cases if "choice_id" not in c.answer]
    assert all((c.raw_latex is None) != (c.raw_keys is None) for c in typed)
