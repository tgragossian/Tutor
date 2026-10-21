from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from mathtutor.content.loader import LoadedContent, load_bundle
from mathtutor.domain import FormatIssueCode
from mathtutor.verify import content_check
from mathtutor.verify.content_check import check_bundle, main
from mathtutor.verify.types import CheckResult, FormatIssue

ROOT = Path(__file__).resolve().parents[3]
REAL = ROOT / "content" / "compiled" / "problems.json"
BUNDLES = ROOT / "tests" / "fixtures" / "content" / "bundles"


def load(name: str) -> LoadedContent:
    return load_bundle(BUNDLES / f"{name}.json")


def test_seed_bundle_passes() -> None:
    assert check_bundle(load_bundle(REAL)) == []


def test_expected_answer_must_translate() -> None:
    errors = check_bundle(load("expected_untranslatable"))
    assert len(errors) == 1
    assert errors[0].startswith("untranslatable-001: answer.latex: does not translate")


def test_expected_answer_undefined_on_domain() -> None:
    errors = check_bundle(load("expected_pole"))  # 1/x on R (spec 04 row 7)
    assert len(errors) == 1
    assert errors[0].startswith("pole-001: answer.domain: expected answer undefined on domain")


def test_choices_each_translate_and_correct_differs() -> None:
    errors = check_bundle(load("choice_bad"))
    assert len(errors) == 1
    assert errors[0].startswith("choice-001: answer.choices[1]:")
    assert "provably equal" in errors[0]


def _edited(tmp_path: Path, edit: Any) -> LoadedContent:
    data = json.loads((BUNDLES / "good.json").read_text(encoding="utf-8"))
    edit(data["problems"])
    path = tmp_path / "b.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return load_bundle(path)


def test_misconceptions_are_not_correct(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["misconceptions"] = ["3x^2  # same as the answer", "2x  # wrong"]
        problems[0]["misconceptions_mathjson"] = [
            ["InvisibleOperator", 3, ["Power", "x", 2]],
            ["InvisibleOperator", 2, "x"],
        ]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors == ["pow-001: misconceptions[0]: graded correct against the expected answer"]


def test_null_misconception_is_skipped(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["misconceptions"] = ["\\frac{1}{  # unparsable"]
        problems[0]["misconceptions_mathjson"] = [None]

    assert check_bundle(_edited(tmp_path, edit)) == []


def test_choice_misconception_naming_the_correct_choice(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[1]["misconceptions"] = ["a  # is the right one", "z  # no such choice"]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors[0] == "pow-002: misconceptions[0]: graded correct against the expected answer"
    assert "not a choice id" in errors[1]


def test_domain_abstention_reports_unprovable(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        # ln of a transcendental argument: the exact machinery cannot decide where it is positive
        problems[0]["answer"]["mathjson"] = ["Ln", ["Add", ["Exp", "x"], ["Sin", "x"]]]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors and "answer.domain: domain unprovable" in errors[0]


def test_cli_ok_and_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(REAL)]) == 0
    assert capsys.readouterr().out == f"ok: {len(load_bundle(REAL).bundle.problems)} problems\n"
    assert main([str(BUNDLES / "expected_pole.json")]) == 1
    assert "pole-001: answer.domain" in capsys.readouterr().out


def test_cli_as_module() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mathtutor.verify.content_check", str(REAL)],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == f"ok: {len(load_bundle(REAL).bundle.problems)} problems\n"


def test_same_domain_defect_is_reported_once(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        # two constraints (x != 0 and x^2 != 0) fail at the same point
        problems[0]["answer"]["mathjson"] = [
            "Add",
            ["Divide", 1, "x"],
            ["Divide", 1, ["Power", "x", 2]],
        ]

    errors = check_bundle(_edited(tmp_path, edit))
    assert len(errors) == 1 and "undefined on domain" in errors[0]


def test_bare_function_in_answer_latex_is_an_error(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["answer"]["latex"] = r"(1-\sin x)^2"
        problems[0]["answer"]["mathjson"] = ["Power", ["Subtract", 1, ["Sin", "x"]], 2]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors == [r"pow-001: answer.latex: function input needs parentheses (\sin)"]


def test_bare_function_in_choice_is_an_error(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[1]["answer"]["choices"][1]["latex"] = r"x\cos x"
        problems[1]["answer"]["choices"][1]["mathjson"] = ["Multiply", "x", ["Cos", "x"]]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors == [r"pow-002: answer.choices[1].latex: function input needs parentheses (\cos)"]


def test_bare_function_in_misconception_is_an_error(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["misconceptions"] = [r"\sin x  # forgot the chain rule"]
        problems[0]["misconceptions_mathjson"] = [["Sin", "x"]]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors == [r"pow-001: misconceptions[0]: function input needs parentheses (\sin)"]


def test_bare_function_in_uncompiled_misconception_is_an_error(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["misconceptions"] = [r"\sin x  # forgot the chain rule"]
        problems[0]["misconceptions_mathjson"] = [None]

    errors = check_bundle(_edited(tmp_path, edit))
    assert errors == [r"pow-001: misconceptions[0]: function input needs parentheses (\sin)"]


def test_rejected_misconception_is_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["misconceptions"] = ["2x  # wrong"]
        problems[0]["misconceptions_mathjson"] = [["InvisibleOperator", 2, "x"]]

    content = _edited(tmp_path, edit)
    rejected = CheckResult(FormatIssue(FormatIssueCode.INCOMPLETE), "test")
    monkeypatch.setattr(content_check, "check", lambda *args, **kwargs: rejected)
    errors = check_bundle(content)
    assert errors == ["pow-001: misconceptions[0]: misconception is not gradable: incomplete"]


def test_statement_is_not_checked(tmp_path: Path) -> None:
    def edit(problems: list[dict[str, Any]]) -> None:
        problems[0]["statement"] = r"Find the derivative of $\cos x$."

    assert check_bundle(_edited(tmp_path, edit)) == []


def _with_domain(
    tmp_path: Path, mathjson: Any, latex: str, interval: list[str], strict: bool = False
) -> LoadedContent:
    def edit(problems: list[dict[str, Any]]) -> None:
        answer = problems[0]["answer"]
        answer["mathjson"], answer["latex"] = mathjson, latex
        answer["domain"] = {"intervals": [interval], "exclude": []}
        answer["strict_domain"] = strict
        problems[0]["misconceptions"], problems[0]["misconceptions_mathjson"] = [], []

    return _edited(tmp_path, edit)


def test_finite_endpoint_where_answer_is_defined_must_be_closed(tmp_path: Path) -> None:
    """Thomas's rule: plug the endpoint in; a real value means closed, undefined means open."""
    errors = check_bundle(
        _with_domain(tmp_path, ["Sqrt", "x"], r"\sqrt{x}", ["0", "inf", "open", "open"])
    )
    assert len(errors) == 1
    assert "intervals[0] lower end 0 should be closed" in errors[0]
    ok = _with_domain(tmp_path, ["Sqrt", "x"], r"\sqrt{x}", ["0", "inf", "closed", "open"])
    assert check_bundle(ok) == []


def test_finite_endpoint_where_answer_is_undefined_must_be_open(tmp_path: Path) -> None:
    inverse = ["Divide", 1, "x"]
    opened = _with_domain(tmp_path, inverse, r"\frac{1}{x}", ["0", "inf", "open", "open"])
    assert check_bundle(opened) == []
    closed = check_bundle(
        _with_domain(tmp_path, inverse, r"\frac{1}{x}", ["0", "inf", "closed", "open"])
    )
    assert closed and "undefined on domain" in closed[0]


def test_upper_endpoint_rule(tmp_path: Path) -> None:
    root = ["Sqrt", ["Subtract", 4, "x"]]
    errors = check_bundle(
        _with_domain(tmp_path, root, r"\sqrt{4-x}", ["-inf", "4", "open", "open"])
    )
    assert len(errors) == 1 and "intervals[0] upper end 4 should be closed" in errors[0]


def test_strict_domain_intervals_are_the_answer_and_not_adjusted(tmp_path: Path) -> None:
    content = _with_domain(tmp_path, ["Sqrt", "x"], r"\sqrt{x}", ["0", "inf", "open", "open"], True)
    assert not any("should be closed" in e for e in check_bundle(content))
