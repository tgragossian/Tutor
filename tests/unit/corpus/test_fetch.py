"""Corpus snapshot tool: TOC parsing, hashing, fail-closed completeness, host allowlist."""

import hashlib
import json
import re
import urllib.request
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
    (tmp_path / "snapshot.json").write_text("{}", encoding="utf-8")
    code = _run(tmp_path, FakeSource(missing="7cfe0552"))
    assert code != 0
    assert not (tmp_path / "snapshot.json").exists()


def test_redirect_to_foreign_host_exits_1(tmp_path: Path) -> None:
    req = urllib.request.Request("https://openstax.org/x")
    with pytest.raises(ValueError):
        fetch._CheckedRedirects().redirect_request(req, None, 302, "", {}, "https://evil.com/x")

    def redirected(url: str) -> bytes:
        raise ValueError("redirect to https://evil.com/x")

    code = fetch.run(
        out_dir=tmp_path / "raw",
        snapshot_path=tmp_path / "snapshot.json",
        fetcher=redirected,
        sleep=lambda _s: None,
    )
    assert code == 1
    assert not (tmp_path / "snapshot.json").exists()


def test_client_errors_are_not_retried() -> None:
    calls: list[str] = []

    def gone(url: str) -> bytes:
        calls.append(url)
        raise fetch.FetchError("404", retryable=False)

    naps: list[float] = []
    with pytest.raises(fetch.FetchError):
        fetch._get("https://openstax.org/x", gone, naps.append)
    assert len(calls) == 1 and naps == []


def test_server_errors_retry_without_final_sleep() -> None:
    calls: list[str] = []

    def flaky(url: str) -> bytes:
        calls.append(url)
        raise fetch.FetchError("503")

    naps: list[float] = []
    with pytest.raises(fetch.FetchError):
        fetch._get("https://openstax.org/x", flaky, naps.append)
    assert len(calls) == fetch.ATTEMPTS and len(naps) == fetch.ATTEMPTS - 1


def test_committed_snapshot_is_whole_book() -> None:
    path = Path(__file__).resolve().parents[3] / "content" / "corpus" / "snapshot.json"
    toc = json.loads(path.read_text(encoding="utf-8"))["toc"]
    counts = {
        "numbered-section": 45,
        "composite-page": 24,
        "intro": 6,
        "answer-key": 6,
        "appendix": 3,
        "preface": 1,
        "index": 1,
    }
    for kind, n in counts.items():
        assert sum(e["kind"] == kind for e in toc) == n, kind
    assert len(toc) == sum(counts.values())
    sizes = {1: 5, 2: 5, 3: 9, 4: 10, 5: 7, 6: 9}
    for ch, n in sizes.items():
        rows = [e for e in toc if e["slug"].startswith(f"{ch}-") and e["kind"] != "answer-key"]
        kinds = [e["kind"] for e in rows]
        assert kinds == ["intro"] + ["numbered-section"] * n + ["composite-page"] * 4, ch
        assert [e["section"] for e in rows if e["kind"] == "numbered-section"] == [
            f"{ch}.{i}" for i in range(1, n + 1)
        ]
    assert len({e["slug"] for e in toc}) == len(toc)
    for e in toc:
        assert e["bytes"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", e["sha256"])


def test_rate_limit_sleeps_between_requests(tmp_path: Path) -> None:
    naps: list[float] = []
    fetch.run(
        out_dir=tmp_path / "raw",
        snapshot_path=tmp_path / "snapshot.json",
        fetcher=FakeSource(),
        sleep=naps.append,
        now=lambda: "t",
    )
    source = FakeSource()
    fetch.run(
        out_dir=tmp_path / "raw2",
        snapshot_path=tmp_path / "snapshot2.json",
        fetcher=source,
        sleep=lambda _s: None,
        now=lambda: "t",
    )
    assert len(naps) >= len(source.urls)
    assert all(n >= 1.0 for n in naps)


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
