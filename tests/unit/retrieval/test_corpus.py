"""load_corpus verifies the built files against the manifest."""

import json
import re
from pathlib import Path

import pytest
from corpus import build

from mathtutor.retrieval.corpus import (
    MAX_CHUNK_TOKENS,
    ChunkRole,
    CorpusError,
    estimate_tokens,
    load_corpus,
)

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "corpus" / "build"


@pytest.fixture
def corpus_dir(tmp_path: Path) -> Path:
    built = build.build_corpus(FIXTURE / "snapshot.json", FIXTURE / "raw")
    build.write_corpus(built, tmp_path)
    return tmp_path


def test_load_corpus_roundtrip(corpus_dir: Path) -> None:
    corpus = load_corpus(corpus_dir)
    manifest = json.loads((corpus_dir / "manifest.json").read_text(encoding="utf-8"))
    assert corpus.corpus_hash == manifest["corpus_hash"]
    assert corpus.edition == "calculus-volume-1@8dbc2ce"
    assert len(corpus.chunks) == manifest["chunk_count"]
    assert all(isinstance(c.role, ChunkRole) for c in corpus.chunks.values())


def test_load_corpus_rejects_bad_hash(corpus_dir: Path) -> None:
    path = corpus_dir / "chunks.jsonl"
    path.write_bytes(path.read_bytes().replace(b"Constant Rule", b"Constant Rul3", 1))
    with pytest.raises(CorpusError, match="corpus_hash"):
        load_corpus(corpus_dir)


def test_load_corpus_rejects_bad_chunk_hash(corpus_dir: Path) -> None:
    import hashlib

    path = corpus_dir / "chunks.jsonl"
    raw = path.read_bytes().replace(b"Constant Rule", b"Constant Rul3", 1)
    path.write_bytes(raw)
    manifest_path = corpus_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["corpus_hash"] = hashlib.sha256(raw).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CorpusError, match="content_hash"):
        load_corpus(corpus_dir)


def test_load_corpus_missing_files(tmp_path: Path) -> None:
    with pytest.raises(CorpusError):
        load_corpus(tmp_path)


def test_load_corpus_accepts_chunks_file(corpus_dir: Path) -> None:
    assert load_corpus(corpus_dir / "chunks.jsonl") == load_corpus(corpus_dir)


def test_real_corpus_loads() -> None:
    real = Path(__file__).resolve().parents[3] / "content" / "corpus"
    corpus = load_corpus(real / "chunks.jsonl")
    manifest = json.loads((real / "manifest.json").read_text(encoding="utf-8"))
    assert len(corpus.chunks) > 500
    assert corpus.edition.startswith("calculus-volume-1@")
    assert manifest["unavailable_math"] == 0
    id_re = re.compile(r"^c1-\d+\.\d+-(def|thm|rule|ex|txt|exr|key)\d+(-p\d+)?$")
    for chunk in corpus.chunks.values():
        assert id_re.match(chunk.chunk_id)
        assert chunk.est_tokens == estimate_tokens(chunk.text) <= MAX_CHUNK_TOKENS
        assert chunk.url.startswith("https://openstax.org/books/calculus-volume-1/pages/")
