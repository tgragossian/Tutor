"""The chunked textbook corpus: ``chunks.jsonl`` + ``manifest.json`` in one directory.

``chunks.jsonl`` is canonical: one chunk per line, ``json.dumps(..., sort_keys=True,
ensure_ascii=False, separators=(",", ":"))`` plus ``"\\n"``, in book order.  ``corpus_hash`` in the
manifest is the SHA-256 of those exact bytes, and :func:`load_corpus` refuses a corpus whose file,
chunk hashes, count, edition or licence do not match.  Stdlib only (loaded by the web process).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

LICENCE = "CC BY-NC-SA 4.0"
CHUNKS_FILE = "chunks.jsonl"
MANIFEST_FILE = "manifest.json"
MAX_CHUNK_TOKENS = 700


class ChunkRole(StrEnum):
    DEFINITION = "definition"
    THEOREM = "theorem"
    RULE = "rule"
    EXAMPLE = "example"
    EXPLANATION = "explanation"
    EXERCISE = "exercise"
    ANSWER_KEY = "answer_key"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    section: str
    section_title: str
    url: str
    role: ChunkRole
    text: str
    content_hash: str
    est_tokens: int


@dataclass(frozen=True)
class Corpus:
    chunks: dict[str, Chunk]
    corpus_hash: str
    edition: str


class CorpusError(ValueError):
    """The corpus files are missing, malformed or do not match their manifest."""


def estimate_tokens(text: str) -> int:
    """Same estimate as the prompt budget: ``ceil(utf8_bytes / 3)``."""
    return math.ceil(len(text.encode("utf-8")) / 3)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_line(chunk: Chunk) -> str:
    record = asdict(chunk)
    record["role"] = chunk.role.value
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n"


def canonical_jsonl(chunks: list[Chunk]) -> bytes:
    return "".join(chunk_line(c) for c in chunks).encode("utf-8")


def load_corpus(path: Path) -> Corpus:
    """Load the corpus after verifying ``chunks.jsonl`` against ``manifest.json``.

    ``path`` is the corpus directory or its ``chunks.jsonl`` (``Settings.corpus_path``); the
    manifest is always read from the same directory.
    """
    if path.suffix == ".jsonl":
        path = path.parent
    try:
        manifest = json.loads((path / MANIFEST_FILE).read_text(encoding="utf-8"))
        raw = (path / CHUNKS_FILE).read_bytes()
    except (OSError, ValueError) as exc:
        raise CorpusError(f"cannot read corpus at {path}: {exc}") from exc
    if not isinstance(manifest, dict):
        raise CorpusError("manifest is not an object")
    if hashlib.sha256(raw).hexdigest() != manifest.get("corpus_hash"):
        raise CorpusError("corpus_hash does not match chunks.jsonl")
    if manifest.get("licence") != LICENCE:
        raise CorpusError("unexpected corpus licence")
    edition = manifest.get("edition")
    if not isinstance(edition, str) or not edition:
        raise CorpusError("manifest has no edition")
    chunks: dict[str, Chunk] = {}
    for line in raw.decode("utf-8").splitlines():
        try:
            rec = json.loads(line)
            chunk = Chunk(
                chunk_id=rec["chunk_id"],
                section=rec["section"],
                section_title=rec["section_title"],
                url=rec["url"],
                role=ChunkRole(rec["role"]),
                text=rec["text"],
                content_hash=rec["content_hash"],
                est_tokens=int(rec["est_tokens"]),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise CorpusError(f"malformed chunk line: {exc}") from exc
        if chunk.chunk_id in chunks:
            raise CorpusError(f"duplicate chunk id {chunk.chunk_id}")
        if chunk.content_hash != text_hash(chunk.text):
            raise CorpusError(f"content_hash mismatch for {chunk.chunk_id}")
        chunks[chunk.chunk_id] = chunk
    if len(chunks) != manifest.get("chunk_count"):
        raise CorpusError("chunk_count does not match chunks.jsonl")
    return Corpus(chunks=chunks, corpus_hash=manifest["corpus_hash"], edition=edition)
