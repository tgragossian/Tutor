"""Fetch a frozen snapshot of OpenStax Calculus Volume 1 and write its manifest.

Source kind is ``archive_json``: the book tree and each page come from the OpenStax archive
endpoint on openstax.org (the book pages themselves are client-rendered shells).  Raw bytes are
stored untouched, one file per page, and ``snapshot.json`` records each file's SHA-256.  The
manifest is written only after every page in the table of contents was fetched.

Stdlib only.  HTTPS ``openstax.org`` only, one request per second, fixed User-Agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

TOOL_VERSION = "1"
USER_AGENT = "mathtutor-corpus/1 (+https://tutor.thomasgragossian.dev)"
HOST = "openstax.org"
ORIGIN = f"https://{HOST}"
BOOK_SLUG = "calculus-volume-1"
BOOK_ID = "8b89d172-2927-466f-8661-01abc7ccdba4"
SOURCE_KIND = "archive_json"
MIN_INTERVAL_S = 1.0
ATTEMPTS = 3
TIMEOUT_S = 60

Fetcher = Callable[[str], bytes]


class FetchError(RuntimeError):
    def __init__(self, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


def validate_url(url: str) -> None:
    """Reject anything that is not an https URL on exactly openstax.org (no userinfo)."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != HOST or "@" in parts.netloc:
        raise ValueError(f"only https://{HOST} is allowed: {url!r}")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def http_fetch(url: str) -> bytes:
    validate_url(url)
    opener = urllib.request.build_opener(_CheckedRedirects)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(req, timeout=TIMEOUT_S) as resp:
            return bytes(resp.read())
    except urllib.error.HTTPError as exc:
        retryable = exc.code == 429 or exc.code >= 500
        raise FetchError(f"{url}: HTTP {exc.code}", retryable=retryable) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"{url}: {exc}") from exc


@dataclass(frozen=True)
class TocEntry:
    slug: str
    section: str
    title: str
    kind: str
    url: str


class _Text(HTMLParser):
    """Collects visible text and the text of the ``os-number`` span, if any."""

    def __init__(self) -> None:
        super().__init__()
        self.text: list[str] = []
        self.number: list[str] = []
        self._stack: list[bool] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        classes = (dict(attrs).get("class") or "").split()
        self._stack.append("os-number" in classes or (bool(self._stack) and self._stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._stack and self._stack[-1]:
            self.number.append(data)


def _parse_title(markup: str) -> tuple[str, str]:
    p = _Text()
    p.feed(markup)
    squash = lambda parts: re.sub(r"\s+", " ", "".join(parts)).strip()  # noqa: E731
    number, full = squash(p.number), squash(p.text)
    title = full[len(number) :].strip() if number and full.startswith(number) else full
    return number, title


def parse_toc(book_json: bytes, archive_base: str, version: str) -> list[TocEntry]:
    """Every leaf page of the book tree, in book order."""
    tree = json.loads(book_json)["tree"]
    prefix = f"{archive_base}/{BOOK_ID}@{version}"
    out: list[TocEntry] = []

    def walk(node: dict, chapter: str) -> None:
        for child in node.get("contents", []):
            number, title = _parse_title(child.get("title", ""))
            ttype = child.get("toc_type", "")
            if "contents" in child:
                walk(child, re.sub(r"\D", "", number) if ttype == "chapter" else chapter)
                continue
            kind = child.get("toc_target_type", "")
            slug = child["slug"]
            if kind == "numbered-section":
                section = number
            elif kind == "intro":
                section = f"{chapter}.intro"
            elif kind == "composite-page":
                section = f"{chapter}.{slug.split('-', 1)[1]}"
            elif kind == "appendix":
                section = number
            elif kind == "answer-key":
                section = f"answer-key.{slug}"
            else:
                section = slug
            page_id = child["id"].split("@")[0]
            out.append(TocEntry(slug, section, title, kind, f"{prefix}:{page_id}.json"))

    walk(tree, "")
    slugs = [e.slug for e in out]
    if len(set(slugs)) != len(slugs):
        raise FetchError("duplicate slugs in table of contents")
    return out


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _get(url: str, fetcher: Fetcher, sleep: Callable[[float], None]) -> bytes:
    validate_url(url)
    last: Exception | None = None
    for attempt in range(ATTEMPTS):
        try:
            data = fetcher(url)
            sleep(MIN_INTERVAL_S)
            return data
        except FetchError as exc:
            last = exc
            if not exc.retryable or attempt == ATTEMPTS - 1:
                break
            sleep(MIN_INTERVAL_S)
    raise FetchError(str(last))


def _check_page(raw: bytes, url: str) -> None:
    try:
        content = json.loads(raw).get("content")
    except (ValueError, AttributeError) as exc:
        raise FetchError(f"{url}: not a page JSON object") from exc
    if not isinstance(content, str) or not content.strip():
        raise FetchError(f"{url}: page has no content")


def run(
    out_dir: Path,
    snapshot_path: Path,
    fetcher: Fetcher = http_fetch,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], str] | None = None,
    archive_path: str | None = None,
    version: str | None = None,
) -> int:
    snapshot_path.unlink(missing_ok=True)  # never leave a manifest that may disagree with raw files
    stamp = now or (lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    try:
        if archive_path is None or version is None:
            release = json.loads(_get(f"{ORIGIN}/rex/release.json", fetcher, sleep))
            archive_path = archive_path or release["archiveUrl"]
            version = version or release["books"][BOOK_ID]["defaultVersion"]
        assert archive_path is not None and version is not None
        base = f"{ORIGIN}{archive_path}/contents"
        book_url = f"{base}/{BOOK_ID}@{version}.json"
        toc = parse_toc(_get(book_url, fetcher, sleep), base, version)
        edition = f"{BOOK_SLUG}@{version}"
        items: list[dict[str, object]] = []
        for entry in toc:
            raw = _get(entry.url, fetcher, sleep)
            _check_page(raw, entry.url)
            _atomic_write(out_dir / edition / f"{entry.slug}.json", raw)
            items.append(
                {
                    "slug": entry.slug,
                    "section": entry.section,
                    "title": entry.title,
                    "kind": entry.kind,
                    "url": entry.url,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
            )
    except (FetchError, ValueError, KeyError) as exc:
        print(f"corpus fetch failed: {exc}", file=sys.stderr)
        return 1
    snapshot = {
        "edition": edition,
        "base_url": base,
        "fetched_at": stamp(),
        "source_kind": SOURCE_KIND,
        "toc": items,
        "fetch_tool_version": TOOL_VERSION,
    }
    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    _atomic_write(snapshot_path, text.encode("utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True, help="raw page directory")
    ap.add_argument("--snapshot", type=Path, default=root / "content/corpus/snapshot.json")
    ap.add_argument("--archive-path", help="pin, e.g. /apps/archive/20260604.144757")
    ap.add_argument("--version", help="pin the book version, e.g. 8dbc2ce")
    args = ap.parse_args(argv)
    return run(args.out, args.snapshot, archive_path=args.archive_path, version=args.version)


if __name__ == "__main__":
    sys.exit(main())
