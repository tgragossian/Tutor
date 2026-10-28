"""The prompt fingerprint (Q3, Thomas 2026-10-27): rows and runs record the exact text used."""

from __future__ import annotations

import re
import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from support.helpkit import make_kit, output

from mathtutor.help import prompts
from mathtutor.help.prompts import prompt_fingerprint, prompt_id


@pytest.fixture
def copied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A private copy of the prompt folder, so tests may edit it."""
    root = tmp_path / "prompts"
    shutil.copytree(prompts.PROMPTS_DIR, root)
    monkeypatch.setattr(prompts, "PROMPTS_DIR", root)
    prompt_fingerprint.cache_clear()
    yield root / "v1"
    prompt_fingerprint.cache_clear()


def test_fingerprint_is_stable_and_short() -> None:
    assert re.fullmatch(r"[0-9a-f]{12}", prompt_fingerprint("v1"))
    assert prompt_fingerprint("v1") == prompt_fingerprint("v1")
    assert prompt_id("v1") == f"v1+{prompt_fingerprint('v1')}"


def test_any_wording_change_changes_it(copied: Path) -> None:
    before = prompt_fingerprint("v1")
    hint = copied / "hint.md"
    hint.write_bytes(hint.read_bytes().replace(b"hint", b"tip", 1))
    prompt_fingerprint.cache_clear()
    assert prompt_fingerprint("v1") != before


def test_a_new_file_changes_it(copied: Path) -> None:
    before = prompt_fingerprint("v1")
    (copied / "question.md").write_text("Answer the question.", encoding="utf-8")
    prompt_fingerprint.cache_clear()
    assert prompt_fingerprint("v1") != before


def test_line_endings_do_not_change_it(copied: Path) -> None:
    before = prompt_fingerprint("v1")
    for path in copied.glob("*.md"):
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    prompt_fingerprint.cache_clear()
    assert prompt_fingerprint("v1") == before


def test_help_rows_record_the_fingerprint(tmp_path: Path) -> None:
    kit = make_kit(tmp_path, [output()])
    rid = uuid.uuid4()
    kit.help(rid=rid)
    assert kit.row(rid).prompt_version == prompt_id("v1")
