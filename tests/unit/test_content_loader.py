from __future__ import annotations

import json
from pathlib import Path

import pytest
from support.mathjson import meta

from mathtutor.content.loader import ContentError, content_version, load_bundle, servable

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "tests" / "fixtures" / "content" / "bundles"
GOOD = BUNDLES / "good.json"
BAD_TWO = BUNDLES / "bad_two.json"
ORDER = BUNDLES / "order.json"


def test_good_bundle_loads() -> None:
    c = load_bundle(GOOD)
    assert len(c.bundle.problems) == 2
    assert set(c.versions) == {"pow-001", "pow-002"}
    assert len(c.bundle_version) == 12


def test_content_version_ignores_key_order_and_changes_on_edit() -> None:
    a = {"id": "x", "n": 1, "s": "é"}
    assert content_version(a) == content_version({"s": "é", "n": 1, "id": "x"})
    assert content_version(a) != content_version({**a, "n": 2})
    assert len(content_version(a)) == 12


def test_crlf_bundle_same_versions(tmp_path: Path) -> None:
    crlf = tmp_path / "b.json"
    crlf.write_bytes(GOOD.read_bytes().replace(b"\n", b"\r\n"))
    a, b = load_bundle(crlf), load_bundle(GOOD)
    assert a.versions == b.versions
    assert a.bundle_version == b.bundle_version


def test_errors_are_collected() -> None:
    with pytest.raises(ContentError) as exc:
        load_bundle(BAD_TWO)
    msg = str(exc.value)
    assert "duplicate" in msg and "unknown topic" in msg


def test_validation_errors_name_problem_and_field(tmp_path: Path) -> None:
    data = json.loads(GOOD.read_text(encoding="utf-8"))
    data["problems"][0]["strict_domian"] = True
    path = tmp_path / "b.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ContentError) as exc:
        load_bundle(path)
    assert "pow-001: strict_domian:" in str(exc.value)


def test_needs_review_loaded_but_not_servable() -> None:
    c = load_bundle(GOOD)
    assert len(c.bundle.problems) == 2
    assert [p.id for p in servable(c)] == ["pow-001"]


def test_servable_order_is_topic_then_difficulty_then_id() -> None:
    assert [p.id for p in servable(load_bundle(ORDER))] == ["c", "a", "b", "z", "d"]


def test_compiled_tools_match_captured_meta() -> None:
    c = load_bundle(ROOT / "content" / "compiled" / "problems.json")
    captured = meta()
    assert c.bundle.tools.model_dump() == {
        "mathlive": captured["mathlive"],
        "compute_engine": captured["compute_engine"],
    }
