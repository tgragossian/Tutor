"""Build deterministic, provenance-carrying chunks of OpenStax Calculus Volume 1.

Reads the frozen snapshot (``content/corpus/snapshot.json`` + raw archive pages under
``data/corpus-raw/<edition>/<slug>.json``), verifies every raw file against its recorded SHA-256,
converts MathML to LaTeX (``$...$`` inline, ``$$...$$`` display) and writes
``content/corpus/chunks.jsonl`` and ``manifest.json``.  The same snapshot always gives
byte-identical output: no timestamps, sorted keys, book order.

Usage: ``uv run python tools/corpus/build.py [--snapshot ...] [--raw ...] [--out ...]``.

Chunking (see content/corpus/README.md, "Chunks"):

- Numbered sections: prose runs under one heading become ``txt`` (explanation) chunks; boxes
  become ``def``/``thm``/``rule``/``ex`` chunks; checkpoints, student projects and the section
  exercise list become ``exr`` (exercise).  Media boxes and images are skipped.
- Chapter pages use section ``N.0``: key terms ``def``, key equations ``rule``, review exercises
  ``exr``.  Key concepts are filed under the section they summarize (``txt``).
- Answer keys become ``key`` (answer_key) chunks filed under the exercise's section.
- Chapter openers, preface, appendices and the index are not chunked.
- Target 300-500 estimated tokens, hard ceiling 700.  A box that fits under the ceiling is
  one chunk; a longer one is split into ``-p1``, ``-p2`` ... each starting with the box title.
  A display equation is glued to the sentence before it and to a following lower-case continuation
  ("where ...") so an equation never leaves its conditions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from mathtutor.retrieval.corpus import (
    CHUNKS_FILE,
    LICENCE,
    MANIFEST_FILE,
    MAX_CHUNK_TOKENS,
    Chunk,
    ChunkRole,
    canonical_jsonl,
    estimate_tokens,
    text_hash,
)
from mathtutor.retrieval.mathml import local, math_to_latex

BUILD_VERSION = "1"
NORMALIZER = "nfc-ws-mathml-1"
PAGE_BASE = "https://openstax.org/books/calculus-volume-1/pages/"
SOFT_TOKENS = 500
MIN_TOKENS = 300
INCLUDED_KINDS = frozenset(["numbered-section", "composite-page", "answer-key"])

ROLE_OF_KIND = {
    "def": ChunkRole.DEFINITION,
    "thm": ChunkRole.THEOREM,
    "rule": ChunkRole.RULE,
    "ex": ChunkRole.EXAMPLE,
    "txt": ChunkRole.EXPLANATION,
    "exr": ChunkRole.EXERCISE,
    "key": ChunkRole.ANSWER_KEY,
}
BLOCK_TAGS = frozenset(
    "p div section ul ol li table thead tbody tr figure dl dt dd h1 h2 h3 h4 h5 h6 "
    "figcaption".split()
)
SKIP_TAGS = frozenset(["script", "style", "head", "img", "figure"])
_LABEL = re.compile(r"^[\w.()]{1,12}[.:]?$")
_WS = re.compile(r"\s+")

__all__ = ["BuildError", "Built", "Chunk", "build_corpus", "write_corpus"]


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class Unit:
    text: str
    anchor: str
    display: bool = False


@dataclass
class Draft:
    section: str
    section_title: str
    slug: str
    anchor: str
    kind: str
    text: str
    order: tuple[int, int, int, int]
    group: int | None = None


@dataclass
class Built:
    chunks: list[Chunk]
    manifest: dict[str, object]
    jsonl: bytes
    stats: dict[str, int] = field(default_factory=dict)


def norm(text: str) -> str:
    return _WS.sub(" ", unicodedata.normalize("NFC", text).replace("\xa0", " ")).strip()


def section_key(section: str) -> tuple[int, int]:
    major, minor = section.split(".")
    return int(major), int(minor)


def classes(el: ET.Element) -> set[str]:
    return set((el.get("class") or "").split())


# --- packing -----------------------------------------------------------------------------------


def glue(units: list[Unit]) -> list[list[Unit]]:
    """Group units so a display equation stays with its lead-in and its conditions."""
    groups: list[list[Unit]] = []
    for u in units:
        if groups and (u.display or (groups[-1][-1].display and u.text[:1].islower())):
            groups[-1].append(u)
        else:
            groups.append([u])
    return groups


def _math_mask(text: str) -> list[bool]:
    """True for characters inside $...$ or $$...$$ (escaped \\$ does not toggle)."""
    mask: list[bool] = []
    inside = False
    i = 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            mask += [inside, inside]
            i += 2
            continue
        if text[i] == "$":
            width = 2 if text.startswith("$$", i) else 1
            mask += [True] * width
            inside = not inside
            i += width
            continue
        mask.append(inside)
        i += 1
    return mask


def _split_prose(text: str, budget: int) -> list[str]:
    """Split at sentence ends outside math; fall back to spaces outside math, then spaces."""
    mask = _math_mask(text)
    cuts = [m.end() for m in re.finditer(r"[.?!:;] ", text) if not mask[m.start()]]
    if not cuts:
        cuts = [m.end() for m in re.finditer(" ", text) if not mask[m.start()]]
    if not cuts:
        cuts = [m.end() for m in re.finditer(" ", text)]
    pieces: list[str] = []
    start = 0
    last_ok = None
    for cut in cuts + [len(text)]:
        if estimate_tokens(text[start:cut]) > budget and last_ok is not None:
            pieces.append(text[start:last_ok].strip())
            start = last_ok
        last_ok = cut
    pieces.append(text[start:].strip())
    return [p for p in pieces if p]


def _split_array(text: str) -> list[str] | None:
    """Split ``$$\\begin{array}{..}rows\\end{array}$$`` at its top-level row breaks."""
    m = re.match(r"^\$\$\\begin\{array\}\{([a-z]+)\}(.*)\\end\{array\}(.*)\$\$$", text, re.S)
    if not m:
        return None
    spec, body, trail = m.groups()
    rows: list[str] = []
    depth, start, i = 0, 0, 0
    while i < len(body):
        if body.startswith(r"\begin{", i):
            depth += 1
        elif body.startswith(r"\end{", i):
            depth -= 1
        elif depth == 0 and body.startswith(r" \\ ", i):
            rows.append(body[start:i])
            start = i + 4
            i = start
            continue
        i += 1
    rows.append(body[start:])
    if len(rows) < 2:
        return None
    return [
        "$$\\begin{array}{"
        + spec
        + "}"
        + r
        + "\\end{array}"
        + (trail if k == len(rows) - 1 else "")
        + "$$"
        for k, r in enumerate(rows)
    ]


class Packer:
    def __init__(self) -> None:
        self.forced_splits = 0

    def fit_unit(self, u: Unit, budget: int) -> list[Unit]:
        if estimate_tokens(u.text) <= budget:
            return [u]
        rows = _split_array(u.text) if u.display else None
        if rows:
            out: list[Unit] = []
            for r in rows:
                out.extend(self.fit_unit(Unit(r, u.anchor, True), budget))
            return out
        self.forced_splits += 1 if u.display else 0
        return [Unit(p, u.anchor, u.display) for p in _split_prose(u.text, budget)]

    def pack(self, header: str, groups: list[list[Unit]], *, box: bool) -> list[tuple[str, str]]:
        """Return (anchor, text) chunks, each starting with ``header``."""

        def size(units: list[Unit]) -> int:
            return estimate_tokens(header + "\n" + "\n".join(u.text for u in units))

        flat = [u for g in groups for u in g]
        if not flat:
            return []
        if box and size(flat) <= MAX_CHUNK_TOKENS:
            return [(flat[0].anchor, header + "\n" + "\n".join(u.text for u in flat))]
        budget = MAX_CHUNK_TOKENS - estimate_tokens(header + "\n") - 2
        chunks: list[list[Unit]] = []
        current: list[Unit] = []
        for g in groups:
            if size(g) > MAX_CHUNK_TOKENS:
                pieces = [p for u in g for p in self.fit_unit(u, min(budget, SOFT_TOKENS))]
                g_parts: list[list[Unit]] = [[p] for p in pieces]
            else:
                g_parts = [g]
            for part in g_parts:
                if current and size(current + part) > SOFT_TOKENS:
                    chunks.append(current)
                    current = []
                current = current + part
        if current:
            chunks.append(current)
        if len(chunks) >= 2 and size(chunks[-1]) < MIN_TOKENS:
            if size(chunks[-2] + chunks[-1]) <= MAX_CHUNK_TOKENS:
                chunks[-2:] = [chunks[-2] + chunks[-1]]
        return [(c[0].anchor, header + "\n" + "\n".join(u.text for u in c)) for c in chunks]


# --- page rendering ----------------------------------------------------------------------------


class Renderer:
    """HTML (XHTML) -> units of normalized text with LaTeX math."""

    def __init__(self) -> None:
        self.unavailable_math = 0
        self.math_count = 0
        self.skip: set[int] = set()
        self.skipped_solutions = 0
        self.skip_solutions = False
        self.label_only = 0

    def math(self, el: ET.Element) -> str:
        result = math_to_latex(el)
        self.math_count += 1
        self.unavailable_math += result.unavailable
        if not result.latex:
            return ""
        if el.get("display") == "block":
            return "$$" + result.latex + "$$"
        return " $" + result.latex + "$ "

    def text(self, el: ET.Element) -> str:
        """Inline rendering of a title, term or cell (math included)."""
        parts: list[str] = []
        self.inline(el, parts)
        return norm("".join(parts))

    def inline(self, el: ET.Element, out: list[str]) -> None:
        if el.text:
            out.append(el.text)
        for c in el:
            self.inline_child(c, out)
            if c.tail:
                out.append(c.tail)

    def inline_child(self, c: ET.Element, out: list[str]) -> None:
        tag = local(c.tag)
        if id(c) in self.skip or tag in SKIP_TAGS or c.get("data-type") == "media":
            return
        if tag == "math":
            out.append(self.math(c))
        elif tag == "br":
            out.append(" ")
        elif tag in ("sup", "sub"):
            out.append(("^" if tag == "sup" else "_") + "".join(c.itertext()))
        else:
            self.inline(c, out)

    def is_block(self, c: ET.Element) -> bool:
        return local(c.tag) in BLOCK_TAGS

    def units(self, el: ET.Element, anchor: str) -> list[Unit]:
        anchor = el.get("id") or anchor
        out: list[Unit] = []
        buf: list[str] = [el.text or ""]
        carry = ""

        def flush() -> None:
            nonlocal carry
            text = norm("".join(buf))
            buf.clear()
            if text:
                out.append(Unit(norm(carry + " " + text), anchor))
                carry = ""

        for c in el:
            if id(c) in self.skip or local(c.tag) in SKIP_TAGS:
                buf.append(c.tail or "")
                continue
            if self.is_block(c):
                pending = norm("".join(buf))
                if pending and _LABEL.match(pending):
                    carry = norm(carry + " " + pending)
                    buf.clear()
                else:
                    flush()
                block = self.block(c, anchor)
                if block and carry:
                    first = block[0]
                    block[0] = Unit(norm(carry + " " + first.text), first.anchor, first.display)
                    carry = ""
                out.extend(block)
            else:
                self.inline_child(c, buf)
            buf.append(c.tail or "")
        flush()
        if carry:  # a bare item number whose content was only an image
            self.label_only += 1
        return out

    def block(self, c: ET.Element, anchor: str) -> list[Unit]:
        tag = local(c.tag)
        dtype = c.get("data-type")
        own = c.get("id") or anchor
        if dtype == "solution" and self.skip_solutions:
            self.skipped_solutions += 1
            return []
        if dtype == "equation":
            parts: list[str] = []
            self.inline(c, parts)
            text = norm("".join(parts))
            return [Unit(text, own, display=True)] if text else []
        if tag in ("ul", "ol"):
            return self.listing(c, own)
        if tag == "table":
            rows = []
            for tr in c.iter():
                if local(tr.tag) != "tr":
                    continue
                cells = []
                for td in tr:
                    parts = []
                    self.inline(td, parts)
                    cells.append(norm("".join(parts)))
                row = " | ".join(x for x in cells if x)
                if row:
                    rows.append(Unit(row, own))
            return rows
        if tag == "dl":
            out: list[Unit] = []
            term = ""
            for d in c:
                if local(d.tag) == "dt":
                    term = self.text(d)
                elif local(d.tag) == "dd":
                    body = self.units(d, own)
                    if body:
                        body[0] = Unit(norm(f"{term}: {body[0].text}"), body[0].anchor)
                    out.extend(body)
            return out
        return self.units(c, anchor)

    def listing(self, el: ET.Element, anchor: str) -> list[Unit]:
        ordered = local(el.tag) == "ol"
        style = el.get("type", "1")
        n = int(el.get("start", "1"))
        out: list[Unit] = []
        for li in el:
            if local(li.tag) != "li":
                continue
            items = self.units(li, anchor)
            if not items:
                continue
            mark = _marker(style, n) if ordered else "-"
            n += 1
            first = items[0]
            items[0] = Unit(f"{mark} {first.text}", first.anchor, first.display)
            out.extend(items)
        return out


def _marker(style: str, n: int) -> str:
    if style == "a":
        return chr(ord("a") + (n - 1) % 26) + "."
    if style == "i":
        romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"]
        return (romans[n - 1] if n <= len(romans) else str(n)) + "."
    return f"{n}."


# --- page walkers ------------------------------------------------------------------------------


@dataclass
class PageInfo:
    slug: str
    section: str
    title: str
    kind: str
    toc_index: int


class Builder:
    def __init__(self, toc: list[dict[str, str]]) -> None:
        self.renderer = Renderer()
        self.packer = Packer()
        self.drafts: list[Draft] = []
        self.seq = 0
        self.group_seq = 0
        self.slug_section: dict[str, tuple[str, str]] = {}
        for e in toc:
            if e["kind"] == "numbered-section":
                self.slug_section[e["slug"]] = (e["section"], e["title"])
            elif e["kind"] == "composite-page":
                chapter = e["section"].split(".")[0]
                self.slug_section[e["slug"]] = (f"{chapter}.0", f"Chapter {chapter} {e['title']}")

    # emitting
    def emit(
        self,
        page: PageInfo,
        section: str,
        section_title: str,
        kind: str,
        header: str,
        groups: list[list[Unit]],
        *,
        box_anchor: str | None = None,
    ) -> None:
        header = norm(header)
        parts = self.packer.pack(header, groups, box=box_anchor is not None)
        group = None
        if box_anchor is not None and len(parts) > 1:
            self.group_seq += 1
            group = self.group_seq
        major, minor = section_key(section)
        for anchor, text in parts:
            self.seq += 1
            self.drafts.append(
                Draft(
                    section=section,
                    section_title=section_title,
                    slug=page.slug,
                    anchor=box_anchor or anchor,
                    kind=kind,
                    text=text,
                    order=(major, minor, page.toc_index, self.seq),
                    group=group,
                )
            )

    # numbered sections
    def numbered(self, page: PageInfo, root: ET.Element) -> None:
        body = _page_div(root)
        self.walk(page, body, page.title, body.get("id") or page.slug)

    def walk(self, page: PageInfo, el: ET.Element, heading: str, anchor: str) -> None:
        r = self.renderer
        run: list[Unit] = []

        def flush() -> None:
            if run:
                self.emit(page, page.section, page.title, "txt", heading, glue(run))
                run.clear()

        for c in el:
            tag = local(c.tag)
            dtype = c.get("data-type")
            cls = classes(c)
            if tag in SKIP_TAGS:
                continue
            if tag in ("h2", "h3", "h4") and dtype in ("document-title", "title"):
                if dtype == "title":
                    flush()
                    heading = self.renderer.text(c)
                continue
            if dtype == "abstract":
                flush()
                items = [u for li in c if local(li.tag) == "ul" for u in r.listing(li, anchor)]
                self.emit(
                    page,
                    page.section,
                    page.title,
                    "txt",
                    "Learning Objectives",
                    [items] if items else [],
                )
                continue
            if dtype == "example":
                flush()
                self.example(page, c)
                continue
            if dtype == "note":
                flush()
                self.note(page, c)
                continue
            if "os-section-exercises-container" in cls:
                flush()
                self.exercises(page, c, page.section, page.title)
                continue
            if tag == "section":
                flush()
                self.walk(page, c, heading, c.get("id") or anchor)
                continue
            run.extend(r.block(c, anchor))
        flush()

    def box_title(self, box: ET.Element) -> tuple[str, str]:
        """(label like 'Example 3.17', subtitle) and mark both headings as consumed."""
        label = ""
        subtitle = ""
        for h in box.iter():
            if local(h.tag) == "h3" and "os-title" in classes(h) and not label:
                label = self.renderer.text(h)
                self.renderer.skip.add(id(h))
            elif local(h.tag) == "h4" and (
                h.get("data-type") == "title" or "os-subtitle" in classes(h)
            ):
                if not subtitle:
                    subtitle = self.renderer.text(h)
                    self.renderer.skip.add(id(h))
        return label, subtitle

    def example(self, page: PageInfo, box: ET.Element) -> None:
        label, subtitle = self.box_title(box)
        header = f"{label}: {subtitle}" if subtitle else label
        units = self.renderer.units(box, box.get("id") or "")
        self.emit(
            page, page.section, page.title, "ex", header, glue(units), box_anchor=box.get("id")
        )

    def note(self, page: PageInfo, box: ET.Element) -> None:
        cls = classes(box)
        if "media-2" in cls:
            return
        label, subtitle = self.box_title(box)
        header = f"{label}: {subtitle}" if subtitle else label
        if "checkpoint" in cls or "project" in cls:
            kind = "exr"
        elif "theorem" in cls:
            kind = "thm"
        elif "problem-solving" in cls or label.startswith("Rule"):
            kind = "rule"
        else:
            kind = "def"
        r = self.renderer
        r.skip_solutions = kind == "exr"
        units = r.units(box, box.get("id") or "")
        r.skip_solutions = False
        self.emit(
            page, page.section, page.title, kind, header, glue(units), box_anchor=box.get("id")
        )

    def exercises(
        self, page: PageInfo, container: ET.Element, section: str, title: str, header: str = ""
    ) -> None:
        r = self.renderer
        groups: list[list[Unit]] = []
        r.skip_solutions = True
        for el in container.iter():
            if local(el.tag) == "h3" and not header:
                header = self.renderer.text(el)
        for el in _exercise_items(container):
            units = r.units(el, el.get("id") or container.get("id") or page.slug)
            if units:
                groups.append(units)
        r.skip_solutions = False
        self.emit(page, section, title, "exr", header or f"{title} Exercises", groups)

    # composite pages
    def composite(self, page: PageInfo, root: ET.Element) -> None:
        body = _page_div(root)
        section, title = self.slug_section[page.slug]
        name = page.section.split(".", 1)[1]
        anchor = body.get("id") or page.slug
        r = self.renderer
        if name == "key-terms":
            units = [u for dl in body.iter() if local(dl.tag) == "dl" for u in r.block(dl, anchor)]
            self.emit(page, section, title, "def", title, [[u] for u in units])
        elif name == "key-equations":
            units = [u for t in body.iter() if local(t.tag) == "table" for u in r.block(t, anchor)]
            self.emit(page, section, title, "rule", title, [[u] for u in units])
        elif name == "review-exercises":
            self.exercises(page, body, section, title, header=title)
        elif name == "key-concepts":
            for area in body.iter():
                if "os-section-area" not in classes(area):
                    continue
                link = next((a for a in area.iter() if a.get("data-page-slug")), None)
                if link is None or link.get("data-page-slug") not in self.slug_section:
                    raise BuildError(f"{page.slug}: key-concepts area with unknown section")
                sec, sec_title = self.slug_section[link.get("data-page-slug") or ""]
                r.skip.add(id(link))
                units = r.units(area, anchor)
                self.emit(
                    page,
                    sec,
                    sec_title,
                    "txt",
                    f"Key Concepts: {sec} {sec_title}",
                    [[u] for u in units],
                )
        else:
            raise BuildError(f"{page.slug}: unknown composite page {page.section}")

    # answer keys
    def answer_key(self, page: PageInfo, root: ET.Element) -> None:
        body = _page_div(root)
        r = self.renderer
        for area in body:
            if "os-solution-area" not in classes(area):
                continue
            heading = next((self.renderer.text(h) for h in area if local(h.tag) == "h3"), "Answers")
            batches: list[tuple[str, list[list[Unit]]]] = []
            for sol in area:
                if sol.get("data-type") != "solution":
                    continue
                link = next((a for a in sol.iter() if a.get("data-page-slug")), None)
                target = link.get("data-page-slug") if link is not None else None
                if target not in self.slug_section:
                    raise BuildError(f"{page.slug}: solution {sol.get('id')} has unknown target")
                units = r.units(sol, sol.get("id") or page.slug)
                if batches and batches[-1][0] == target:
                    batches[-1][1].append(units)
                else:
                    batches.append((target, [units]))
            for target, groups in batches:
                sec, sec_title = self.slug_section[target]
                label = heading if heading != "Review Exercises" else sec_title
                self.emit(page, sec, sec_title, "key", f"Answers: {label}", groups)

    # ids
    def finish(self) -> list[Chunk]:
        drafts = sorted(self.drafts, key=lambda d: d.order)
        counters: Counter[tuple[str, str]] = Counter()
        group_ids: dict[int, tuple[str, int]] = {}
        chunks: list[Chunk] = []
        for d in drafts:
            if d.group is not None and d.group in group_ids:
                base, part = group_ids[d.group]
                group_ids[d.group] = (base, part + 1)
                chunk_id = f"{base}-p{part + 1}"
            else:
                counters[(d.section, d.kind)] += 1
                base = f"c1-{d.section}-{d.kind}{counters[(d.section, d.kind)]}"
                if d.group is not None:
                    group_ids[d.group] = (base, 1)
                    chunk_id = f"{base}-p1"
                else:
                    chunk_id = base
            text = d.text
            tokens = estimate_tokens(text)
            if tokens > MAX_CHUNK_TOKENS:
                raise BuildError(f"{chunk_id} is {tokens} estimated tokens")
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    section=d.section,
                    section_title=d.section_title,
                    url=f"{PAGE_BASE}{d.slug}#{d.anchor}",
                    role=ROLE_OF_KIND[d.kind],
                    text=text,
                    content_hash=text_hash(text),
                    est_tokens=tokens,
                )
            )
        return chunks


def _page_div(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if el.get("data-type") in ("page", "composite-page"):
            return el
    raise BuildError("page has no content div")


def _exercise_items(container: ET.Element) -> list[ET.Element]:
    """Exercise divs and the instruction paragraphs between them, in document order."""
    out: list[ET.Element] = []

    def visit(el: ET.Element) -> None:
        for c in el:
            if c.get("data-type") in ("exercise", "equation") or local(c.tag) in (
                "p",
                "ul",
                "ol",
                "table",
            ):
                out.append(c)
            elif local(c.tag) in ("section", "div") and c.get("data-type") not in (
                "solution",
                "note",
            ):
                visit(c)

    visit(container)
    return out


# --- top level ---------------------------------------------------------------------------------


def canonical_snapshot_sha(snapshot: dict[str, object]) -> str:
    """SHA-256 of the snapshot manifest without its fetch timestamp."""
    stable = {k: v for k, v in snapshot.items() if k != "fetched_at"}
    blob = json.dumps(stable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_corpus(snapshot_path: Path, raw_root: Path) -> Built:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    edition = snapshot["edition"]
    toc = snapshot["toc"]
    builder = Builder(toc)
    for index, entry in enumerate(toc):
        if entry["kind"] not in INCLUDED_KINDS:
            continue
        raw_path = raw_root / edition / f"{entry['slug']}.json"
        try:
            raw = raw_path.read_bytes()
        except OSError as exc:
            raise BuildError(f"{entry['slug']}: raw page missing ({exc})") from exc
        if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise BuildError(f"{entry['slug']}: raw page does not match snapshot sha256")
        try:
            root = ET.fromstring(json.loads(raw)["content"])
        except (ValueError, KeyError, ET.ParseError) as exc:
            raise BuildError(f"{entry['slug']}: cannot parse page ({exc})") from exc
        page = PageInfo(entry["slug"], entry["section"], entry["title"], entry["kind"], index)
        builder.renderer.skip.clear()  # ids are only unique while this page's tree is alive
        if entry["kind"] == "numbered-section":
            builder.numbered(page, root)
        elif entry["kind"] == "composite-page":
            builder.composite(page, root)
        else:
            builder.answer_key(page, root)
    chunks = builder.finish()
    jsonl = canonical_jsonl(chunks)
    role_counts = Counter(c.role.value for c in chunks)
    section_counts = Counter(c.section for c in chunks)
    manifest: dict[str, object] = {
        "edition": edition,
        "snapshot_sha256": canonical_snapshot_sha(snapshot),
        "build_version": BUILD_VERSION,
        "normalizer": NORMALIZER,
        "chunk_count": len(chunks),
        "role_counts": dict(sorted(role_counts.items())),
        "section_counts": dict(sorted(section_counts.items(), key=lambda kv: section_key(kv[0]))),
        "unavailable_math": builder.renderer.unavailable_math,
        "corpus_hash": hashlib.sha256(jsonl).hexdigest(),
        "licence": LICENCE,
    }
    stats = {
        "math_elements": builder.renderer.math_count,
        "forced_display_splits": builder.packer.forced_splits,
        "skipped_solutions": builder.renderer.skipped_solutions,
        "image_only_items": builder.renderer.label_only,
    }
    return Built(chunks=chunks, manifest=manifest, jsonl=jsonl, stats=stats)


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_corpus(built: Built, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write(out_dir / CHUNKS_FILE, built.jsonl)
    manifest = json.dumps(built.manifest, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(out_dir / MANIFEST_FILE, manifest.encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--snapshot", type=Path, default=Path("content/corpus/snapshot.json"))
    parser.add_argument("--raw", type=Path, default=Path("data/corpus-raw"))
    parser.add_argument("--out", type=Path, default=Path("content/corpus"))
    args = parser.parse_args(argv)
    try:
        built = build_corpus(args.snapshot, args.raw)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1
    write_corpus(built, args.out)
    summary = {k: built.manifest[k] for k in ("chunk_count", "role_counts", "unavailable_math")}
    print(json.dumps({**summary, **built.stats, "bytes": len(built.jsonl)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
