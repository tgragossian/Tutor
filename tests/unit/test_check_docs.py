from pathlib import Path

from check_docs import check


def write(root: Path, name: str, text: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_too_long_file_reported(tmp_path):
    write(tmp_path, "a.md", "x\n" * 101)
    assert any("a.md" in p and "101 lines" in p for p in check(tmp_path))


def test_broken_relative_link_reported(tmp_path):
    write(tmp_path, "a.md", "[b](missing.md)\n")
    assert any("missing.md" in p for p in check(tmp_path))


def test_anchor_http_and_fenced_links_ok(tmp_path):
    write(tmp_path, "b.md", "# B\n")
    write(
        tmp_path,
        "a.md",
        "[b](b.md#b) [w](https://x.org) `[c](no2.md)`\n```\n[no](nope.md)\n```\n",
    )
    assert check(tmp_path) == []


def test_excluded_dirs_skipped(tmp_path):
    write(tmp_path, "node_modules/x.md", "x\n" * 500)
    assert check(tmp_path) == []
