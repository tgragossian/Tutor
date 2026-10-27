"""Corpus snapshot tool: TOC parsing, hashing, fail-closed completeness, host allowlist."""

import hashlib
import json
from pathlib import Path

import pytest
from corpus import fetch

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "corpus"
BOOK = (FIXTURES / "book.json").read_bytes()
PAGE = (FIXTURES / "page.json").read_bytes()
RELEASE = json.dumps(
    {
        "archiveUrl": "/apps/archive/20260101.000000",
        "books": {fetch.BOOK_ID: {"defaultVersion": "abc1234"}},
    }
).encode()


class FakeSource:
    """Serves release.json, the book tree and a stock page; records every URL."""

    def __init__(self, missing: str | None = None) -> None:
        self.urls: list[str] = []
        self.missing = missing

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        if url.endswith("release.json"):
            return RELEASE
        if self.missing and self.missing in url:
            raise fetch.FetchError(f"404 for {url}")
        if ":" not in url.rsplit("/", 1)[-1]:
            return BOOK
        return PAGE


def _run(tmp_path: Path, source: FakeSource) -> int:
    return fetch.run(
        out_dir=tmp_path / "raw",
        snapshot_path=tmp_path / "snapshot.json",
        fetcher=source,
        sleep=lambda _s: None,
        now=lambda: "2026-10-26T00:00:00Z",
    )


def _entries() -> list[fetch.TocEntry]:
    return fetch.parse_toc(BOOK, "https://openstax.org/apps/archive/x/contents", "abc1234")


def test_toc_complete() -> None:
    got = [(e.slug, e.kind) for e in _entries()]
    assert got[0] == ("preface", "preface")
    chapter1 = [s for s, _ in got if s.startswith("1-")]
    assert chapter1[:3] == [
        "1-introduction",
        "1-1-review-of-functions",
        "1-2-basic-classes-of-functions",
    ]
    assert "1-review-exercises" in chapter1
    assert got.index(("1-review-exercises", "composite-page")) < got.index(
        ("2-introduction", "intro")
    )
    kinds = {k for _, k in got}
    assert {"appendix", "answer-key"} <= kinds
    assert [e.section for e in _entries() if e.slug == "1-1-review-of-functions"] == ["1.1"]
    assert all(e.url.startswith("https://openstax.org/") for e in _entries())
    assert len({e.slug for e in _entries()}) == len(_entries())


def test_snapshot_records_hashes(tmp_path: Path) -> None:
    assert _run(tmp_path, FakeSource()) == 0
    snap = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert snap["source_kind"] == "archive_json"
    assert snap["fetched_at"] == "2026-10-26T00:00:00Z"
    assert snap["edition"] == "calculus-volume-1@abc1234"
    assert [t["slug"] for t in snap["toc"]] == [e.slug for e in _entries()]
    for item in snap["toc"]:
        raw = (tmp_path / "raw" / snap["edition"] / f"{item['slug']}.json").read_bytes()
        assert item["sha256"] == hashlib.sha256(raw).hexdigest()
        assert item["bytes"] == len(raw)


def test_incomplete_fetch_fails(tmp_path: Path) -> None:
    code = _run(tmp_path, FakeSource(missing="7cfe0552"))
    assert code != 0
    assert not (tmp_path / "snapshot.json").exists()


def test_rate_limit_sleeps_between_requests(tmp_path: Path) -> None:
    naps: list[float] = []
    fetch.run(
        out_dir=tmp_path / "raw",
        snapshot_path=tmp_path / "snapshot.json",
        fetcher=FakeSource(),
        sleep=naps.append,
        now=lambda: "t",
    )
    assert naps and all(n >= 1.0 for n in naps)


@pytest.mark.parametrize(
    "url",
    [
        "http://openstax.org/books/x",
        "https://example.com/books/x",
        "https://openstax.org.evil.com/x",
        "https://evil.com/openstax.org",
        "https://user@openstax.org@evil.com/x",
        "ftp://openstax.org/x",
    ],
)
def test_https_openstax_only(url: str) -> None:
    with pytest.raises(ValueError):
        fetch.validate_url(url)


def test_https_openstax_accepts_archive() -> None:
    fetch.validate_url("https://openstax.org/apps/archive/20260101.000000/contents/a.json")
