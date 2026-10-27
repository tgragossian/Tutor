"""Local pure-Python BM25 over the textbook corpus (stdlib only; loaded by the web process)."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from mathtutor.help.config import RetrievalParams
from mathtutor.retrieval.corpus import ChunkRole, Corpus

TOKENIZER_VERSION = "tok-2"

STOPWORDS = frozenset(
    "a an and are as at be but by can for from has have if in is it its of on or so such "
    "that the then this to was we were which will with you your not also into".split()
)
STRUCTURAL_COMMANDS = frozenset(
    "frac dfrac tfrac left right begin end text mathrm mathbf quad qquad displaystyle".split()
)
_TOKEN = re.compile(r"\\([a-z]+)|\\.|([a-z]+)|([0-9]+)|((?<=[a-z'])')")
_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'"})
_INVERSE_TRIG = re.compile(r"\\(sin|cos|tan)\s*\^\s*(?:\{\s*-\s*1\s*\}|-\s*1)")
# Synonym map (tok-2), applied to index and query alike; keep it short:
#   e^{x} / e^x        -> "exponential"
#   "critical number"  -> "critical point"
_EXP_X = re.compile(r"(?<![a-z\\])e\s*\^\s*(?:\{\s*x\s*\}|x)(?![a-z0-9])")
_POSSESSIVE = re.compile(r"(?<=[a-z])'s\b")
_JOINED = re.compile(r"(?<=[a-z])'(?=[a-z])")  # l'hopital -> lhopital; a trailing ' is prime
_SYNONYMS = {("critical", "number"): "point", ("critical", "numbers"): "points"}


def _normalize(text: str) -> str:
    """NFKD accent folding, curly apostrophes to ``'``, lower case, then the rewrites."""
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    text = folded.translate(_QUOTES).lower()
    text = _INVERSE_TRIG.sub(lambda m: f" arc{m.group(1)} ", text)
    text = _EXP_X.sub(" exponential ", text)
    text = _POSSESSIVE.sub("", text)
    return _JOINED.sub("", text)


def tokenize(text: str) -> list[str]:
    """Lowercase letter/digit runs and LaTeX command names; each ``'`` after a letter (or
    another prime) is ``prime``, so ``f''`` gives two.

    tok-2 adds accent folding, apostrophe-joined names (``L'Hôpital`` = ``lhopital``),
    ``\\sin^{-1}`` -> ``arcsin`` (also cos, tan) and the small synonym map above.
    ``\\$`` (an escaped prose dollar sign) and every other backslash escape are dropped, as are
    stopwords and purely structural commands such as ``\\frac``.
    """
    out: list[str] = []
    for m in _TOKEN.finditer(_normalize(text)):
        command, word, digits, prime = m.groups()
        if command is not None:
            if command not in STRUCTURAL_COMMANDS:
                out.append(command)
        elif word is not None:
            if word not in STOPWORDS:
                out.append(word)
        elif digits is not None:
            out.append(digits)
        elif prime is not None:
            out.append("prime")
    return [_SYNONYMS.get((prev, tok), tok) for prev, tok in zip(["", *out], out, strict=False)]


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    score: float


class Bm25Index:
    def __init__(self, corpus: Corpus, params: RetrievalParams) -> None:
        self._corpus = corpus
        self._k1 = params.k1
        self._b = params.b
        self._boost = params.section_boost
        self._postings: dict[str, list[tuple[str, int]]] = {}
        self._lengths: dict[str, int] = {}
        for chunk_id, chunk in corpus.chunks.items():
            tokens = tokenize(chunk.text)
            self._lengths[chunk_id] = len(tokens)
            for term, tf in Counter(tokens).items():
                self._postings.setdefault(term, []).append((chunk_id, tf))
        total = sum(self._lengths.values())
        self._avgdl = total / len(self._lengths) if self._lengths else 0.0
        payload = json.dumps(
            {
                "corpus_hash": corpus.corpus_hash,
                "k1": params.k1,
                "b": params.b,
                "section_boost": params.section_boost,
                "tokenizer": TOKENIZER_VERSION,
            },
            sort_keys=True,
        )
        self.fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def build(cls, corpus: Corpus, params: RetrievalParams) -> Bm25Index:
        return cls(corpus, params)

    def search(
        self,
        query: str,
        k: int,
        *,
        boost_section: str | None,
        roles: frozenset[ChunkRole],
    ) -> list[Hit]:
        """Top ``k`` chunks by raw BM25 score (never normalized); ties break by ``chunk_id``."""
        n_docs = len(self._lengths)
        scores: dict[str, float] = {}
        for term in set(tokenize(query)):
            postings = self._postings.get(term)
            if not postings:
                continue
            df = len(postings)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            for chunk_id, tf in postings:
                norm = 1.0 - self._b + self._b * self._lengths[chunk_id] / self._avgdl
                scores[chunk_id] = scores.get(chunk_id, 0.0) + idf * (
                    tf * (self._k1 + 1.0) / (tf + self._k1 * norm)
                )
        hits: list[Hit] = []
        for chunk_id, score in scores.items():
            chunk = self._corpus.chunks[chunk_id]
            if chunk.role not in roles or score <= 0.0:
                continue
            if boost_section is not None and chunk.section == boost_section:
                score *= self._boost
            hits.append(Hit(chunk_id, score))
        hits.sort(key=lambda h: (-h.score, h.chunk_id))
        return hits[: max(k, 0)]
