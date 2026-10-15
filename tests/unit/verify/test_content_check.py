from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from mathtutor.content.loader import LoadedContent, load_bundle
from mathtutor.verify.content_check import check_bundle, main

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
    assert capsys.readouterr().out == "ok: 6 problems\n"
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
    assert result.stdout == "ok: 6 problems\n"


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
