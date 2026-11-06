"""Corpus chunk builder on a trimmed real snapshot (tests/fixtures/corpus/build)."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from corpus import build
from support.corpus_text import math_spans, prose_in_math

from mathtutor.retrieval.corpus import MAX_CHUNK_TOKENS, ChunkRole, estimate_tokens

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "tests" / "fixtures" / "corpus" / "build"
EDITION = "calculus-volume-1@8dbc2ce"
ID_RE = re.compile(r"^c1-\d+\.\d+-(def|thm|rule|ex|txt|exr|key)\d+(-p\d+)?$")
URL_RE = re.compile(r"^https://openstax\.org/books/calculus-volume-1/pages/[a-z0-9-]+#[\w-]+$")


def run(root: Path = FIXTURE) -> build.Built:
    return build.build_corpus(root / "snapshot.json", root / "raw")


@pytest.fixture(scope="module")
def built() -> build.Built:
    return run()


def by_id(b: build.Built) -> dict[str, build.Chunk]:
    return {c.chunk_id: c for c in b.chunks}


def test_ids_stable_and_unique(built: build.Built) -> None:
    ids = [c.chunk_id for c in built.chunks]
    assert ids and len(ids) == len(set(ids))
    assert all(ID_RE.match(i) for i in ids), [i for i in ids if not ID_RE.match(i)]
    assert ids == [c.chunk_id for c in run().chunks]


def test_rebuild_identical(built: build.Built, tmp_path: Path) -> None:
    build.write_corpus(built, tmp_path / "a")
    build.write_corpus(run(), tmp_path / "b")
    for name in ("chunks.jsonl", "manifest.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()
    raw = (tmp_path / "a" / "chunks.jsonl").read_bytes()
    assert built.manifest["corpus_hash"] == hashlib.sha256(raw).hexdigest()
    # A fresh interpreter with another hash seed must give the same bytes.
    out = tmp_path / "c"
    subprocess.run(
        [
            sys.executable,
            str(REPO / "tools" / "corpus" / "build.py"),
            "--snapshot",
            str(FIXTURE / "snapshot.json"),
            "--raw",
            str(FIXTURE / "raw"),
            "--out",
            str(out),
        ],
        check=True,
        env={**os.environ, "PYTHONHASHSEED": "12345"},
        cwd=REPO,
        capture_output=True,
    )
    for name in ("chunks.jsonl", "manifest.json"):
        assert (out / name).read_bytes() == (tmp_path / "a" / name).read_bytes()


def test_prose_dollar_is_escaped(built: build.Built) -> None:
    texts = "\n".join(c.text for c in built.chunks)
    assert r"approximately \$3." in texts
    assert r"\$83 per drill" in texts
    for c in built.chunks:
        spans = math_spans(c.text)
        assert spans is not None, c.chunk_id
        assert not [s for s in spans if prose_in_math(s)], c.chunk_id


def test_math_mask_honors_escaped_dollar() -> None:
    text = r"costs \$3 and $x$"
    mask = build._math_mask(text)
    assert not any(mask[: text.index("and")])
    assert all(mask[text.index("$x$") : text.index("$x$") + 3])


def test_manifest_fields(built: build.Built) -> None:
    m = built.manifest
    assert set(m) == {
        "edition",
        "snapshot_sha256",
        "build_version",
        "normalizer",
        "chunk_count",
        "role_counts",
        "section_counts",
        "unavailable_math",
        "corpus_hash",
        "licence",
    }
    assert m["edition"] == EDITION
    assert m["chunk_count"] == len(built.chunks) == sum(m["role_counts"].values())
    assert sum(m["section_counts"].values()) == len(built.chunks)
    assert m["unavailable_math"] == 0
    assert "fetched_at" not in json.dumps(m)


def test_every_chunk_has_url_and_licence(built: build.Built) -> None:
    assert built.manifest["licence"] == "CC BY-NC-SA 4.0"
    for c in built.chunks:
        assert URL_RE.match(c.url), c.url


def test_chunks_sorted_in_book_order(built: build.Built) -> None:
    keys = [tuple(int(p) for p in c.section.split(".")) for c in built.chunks]
    assert keys == sorted(keys)


def test_math_kept_as_latex(built: build.Built) -> None:
    thm = by_id(built)["c1-3.3-thm1"]
    assert thm.role is ChunkRole.THEOREM
    assert thm.text.startswith("Theorem 3.2: The Constant Rule")
    assert "If $f(x) = c,$ then $f'(x) = 0.$" in thm.text
    assert r"$$\frac{d}{dx}(c) = 0.$$" in thm.text
    for c in built.chunks:
        assert "<m" not in c.text and "[math unavailable]" not in c.text


def test_equation_stays_with_its_conditions(built: build.Built) -> None:
    thm = by_id(built)["c1-3.3-thm1"].text
    assert "Alternatively, we may express this rule as\n$$" in thm


def test_long_example_split_with_context(built: build.Built) -> None:
    parts = [c for c in built.chunks if re.match(r"c1-3\.2-ex\d+-p\d+$", c.chunk_id)]
    assert len(parts) >= 2
    stem = parts[0].chunk_id.rsplit("-p", 1)[0]
    assert [c.chunk_id for c in parts] == [f"{stem}-p{i}" for i in range(1, len(parts) + 1)]
    title = parts[0].text.split("\n", 1)[0]
    assert title.startswith("Example 3.")
    assert all(c.text.split("\n", 1)[0] == title for c in parts)
    for c in built.chunks:
        assert c.est_tokens == estimate_tokens(c.text) <= MAX_CHUNK_TOKENS


def test_exercises_labeled(built: build.Built) -> None:
    roles = {c.chunk_id: c.role for c in built.chunks}
    exr = [i for i in roles if "-exr" in i]
    keys = [i for i in roles if "-key" in i]
    assert exr and all(roles[i] is ChunkRole.EXERCISE for i in exr)
    assert keys and all(roles[i] is ChunkRole.ANSWER_KEY for i in keys)
    review = [c for c in built.chunks if "/pages/3-review-exercises#" in c.url]
    assert review and all(c.role is ChunkRole.EXERCISE and c.section == "3.0" for c in review)
    answers = [c for c in built.chunks if "/pages/chapter-3#" in c.url]
    assert answers and all(c.role is ChunkRole.ANSWER_KEY for c in answers)
    assert {c.section for c in answers} == {"3.0", "3.3", "3.4"}
    checkpoint = [c for c in built.chunks if c.text.startswith("Checkpoint 3.")]
    assert checkpoint and all(c.role is ChunkRole.EXERCISE for c in checkpoint)


def test_composite_pages_roles(built: build.Built) -> None:
    def roles_on(slug: str) -> set[ChunkRole]:
        return {c.role for c in built.chunks if f"/pages/{slug}#" in c.url}

    assert roles_on("3-key-terms") == {ChunkRole.DEFINITION}
    assert roles_on("3-key-concepts") == {ChunkRole.EXPLANATION}
    concepts = [c for c in built.chunks if "/pages/3-key-concepts#" in c.url]
    assert {c.section for c in concepts} == {"3.3"}
    assert not [c for c in built.chunks if "3-introduction" in c.url]


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "fx"
    shutil.copytree(FIXTURE, root)
    return root


def edit_page(root: Path, slug: str, old: str, new: str) -> None:
    page = root / "raw" / EDITION / f"{slug}.json"
    raw = page.read_bytes()
    assert raw.count(old.encode()) == 1
    raw = raw.replace(old.encode(), new.encode())
    page.write_bytes(raw)
    snap = json.loads((root / "snapshot.json").read_text(encoding="utf-8"))
    for e in snap["toc"]:
        if e["slug"] == slug:
            e["sha256"] = hashlib.sha256(raw).hexdigest()
            e["bytes"] = len(raw)
    (root / "snapshot.json").write_text(json.dumps(snap), encoding="utf-8")


def test_changed_text_changes_hash(built: build.Built, tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    edit_page(root, "3-3-differentiation-rules", "We begin with the basics.", "We start simply.")
    changed = run(root)
    before, after = by_id(built), by_id(changed)
    assert list(before) == list(after)
    diff = [i for i in before if before[i].content_hash != after[i].content_hash]
    assert len(diff) == 1 and "We start simply." in after[diff[0]].text
    assert changed.manifest["corpus_hash"] != built.manifest["corpus_hash"]


def test_snapshot_hash_mismatch_fails(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    page = root / "raw" / EDITION / "3-key-terms.json"
    page.write_bytes(page.read_bytes() + b" ")
    with pytest.raises(build.BuildError, match="3-key-terms"):
        run(root)
