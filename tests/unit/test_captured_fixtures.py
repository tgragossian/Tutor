import json
import re
from pathlib import Path

from support.mathjson import latex, meta, mj

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / "tools/capture/cases.json").read_text(encoding="utf-8"))
PACKAGE = json.loads((ROOT / "tools/package.json").read_text(encoding="utf-8"))
CAPTURED = json.loads((ROOT / "tests/fixtures/mathjson/captured.json").read_text(encoding="utf-8"))


def test_every_case_is_captured_with_all_fields() -> None:
    keys = [c["key"] for c in CASES]
    assert len(keys) == len(set(keys))
    for key in keys:
        case = CAPTURED["cases"][key]
        assert {"input", "latex_out", "mathjson", "mathjson_canonical"} <= case.keys()


def test_versions_match_package_json() -> None:
    deps = PACKAGE["dependencies"]
    assert meta()["mathlive"] == deps["mathlive"]
    assert meta()["compute_engine"] == deps["@cortex-js/compute-engine"]


def test_dependency_versions_are_exact_pins() -> None:
    for name, version in PACKAGE["dependencies"].items():
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), (name, version)


def test_x_plain_roundtrip() -> None:
    assert mj("x_plain") is not None
    assert latex("x_plain") == "x"
