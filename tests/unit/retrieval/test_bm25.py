"""Tokenizer and local BM25 index."""

import math
import time
from pathlib import Path

import psutil
import pytest

from mathtutor.help.config import DEFAULT_CONFIG_PATH, RetrievalParams, load_help_config
from mathtutor.retrieval.bm25 import STOPWORDS, TOKENIZER_VERSION, Bm25Index, tokenize
from mathtutor.retrieval.corpus import Chunk, ChunkRole, Corpus, load_corpus, text_hash

REPO = Path(__file__).resolve().parents[3]
ALL = frozenset(ChunkRole)
PROSE = frozenset({ChunkRole.EXPLANATION, ChunkRole.RULE})


def rss_mb() -> float:
    return psutil.Process().memory_info().rss / 1e6


def params(**kw: float | list[str]) -> RetrievalParams:
    base: dict[str, float | int | list[str]] = {
        "k1": 1.2,
        "b": 0.75,
        "section_boost": 1.3,
        "roles": ["explanation"],
        "query_max_bytes": 1200,
        "question_max_bytes": 500,
    }
    base.update(kw)
    return RetrievalParams.model_validate(base)


def chunk(
    cid: str, text: str, section: str = "1.1", role: ChunkRole = ChunkRole.EXPLANATION
) -> Chunk:
    return Chunk(cid, section, "T", "https://x/" + cid, role, text, text_hash(text), 1)


def corpus_of(*chunks: Chunk, corpus_hash: str = "h1") -> Corpus:
    return Corpus({c.chunk_id: c for c in chunks}, corpus_hash, "ed")


def test_tokenize() -> None:
    got = tokenize(r"The chain rule: $\frac{d}{dx}\sin(7x)$")
    assert got == ["chain", "rule", "d", "dx", "sin", "7", "x"]


def test_tokenize_prime_and_escaped_dollar() -> None:
    assert tokenize(r"f'(x) costs \$5") == ["f", "prime", "x", "costs", "5"]
    assert len(STOPWORDS) == 40


def test_bm25_scores_known_case() -> None:
    corpus = corpus_of(
        chunk("d1", "chain rule chain"),
        chunk("d2", "product rule"),
        chunk("d3", "limit law proof"),
    )
    index = Bm25Index.build(corpus, params())
    hits = index.search("chain rule", 10, boost_section=None, roles=ALL)
    # N=3, avgdl=8/3.  idf(chain)=ln(1+2.5/1.5), idf(rule)=ln(1+1.5/2.5).
    idf_chain, idf_rule = math.log(8 / 3), math.log(1.6)
    avgdl = 8 / 3
    d1_norm = 1.2 * (0.25 + 0.75 * 3 / avgdl)  # 1.3125
    d2_norm = 1.2 * (0.25 + 0.75 * 2 / avgdl)
    d1 = idf_chain * 2 * 2.2 / (2 + d1_norm) + idf_rule * 2.2 / (1 + d1_norm)
    d2 = idf_rule * 2.2 / (1 + d2_norm)
    assert [h.chunk_id for h in hits] == ["d1", "d2"]
    assert hits[0].score == pytest.approx(d1, abs=1e-9)
    assert hits[1].score == pytest.approx(d2, abs=1e-9)
    assert hits[0].score == pytest.approx(1.7499759352196784, abs=1e-9)
    assert hits[1].score == pytest.approx(0.523548346501579, abs=1e-9)


def test_role_filter() -> None:
    corpus = corpus_of(
        chunk("a", "derivative power", role=ChunkRole.EXERCISE),
        chunk("b", "derivative power", role=ChunkRole.ANSWER_KEY),
        chunk("c", "derivative power", role=ChunkRole.RULE),
    )
    index = Bm25Index.build(corpus, params())
    hits = index.search("derivative", 10, boost_section=None, roles=PROSE)
    assert [h.chunk_id for h in hits] == ["c"]


def test_section_boost() -> None:
    corpus = corpus_of(
        chunk("a", "slope tangent", section="2.1"),
        chunk("b", "slope tangent", section="3.6"),
    )
    index = Bm25Index.build(corpus, params())
    plain = index.search("slope", 2, boost_section=None, roles=ALL)
    assert [h.chunk_id for h in plain] == ["a", "b"]
    boosted = index.search("slope", 2, boost_section="3.6", roles=ALL)
    assert [h.chunk_id for h in boosted] == ["b", "a"]
    assert boosted[0].score == pytest.approx(plain[1].score * 1.3, abs=1e-12)


def test_deterministic_ties_and_fingerprint() -> None:
    corpus = corpus_of(chunk("z", "slope"), chunk("m", "slope"), chunk("a", "slope"))
    one = Bm25Index.build(corpus, params())
    two = Bm25Index.build(corpus, params())
    hits = one.search("slope", 3, boost_section=None, roles=ALL)
    assert [h.chunk_id for h in hits] == ["a", "m", "z"]
    assert one.fingerprint == two.fingerprint
    assert Bm25Index.build(corpus, params(k1=1.5)).fingerprint != one.fingerprint
    other = corpus_of(
        chunk("z", "slope"), chunk("m", "slope"), chunk("a", "slope"), corpus_hash="h2"
    )
    assert Bm25Index.build(other, params()).fingerprint != one.fingerprint
    assert TOKENIZER_VERSION == "tok-1"


def test_fingerprint_tracks_tokenizer_version(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = corpus_of(chunk("a", "slope"))
    before = Bm25Index.build(corpus, params()).fingerprint
    monkeypatch.setattr("mathtutor.retrieval.bm25.TOKENIZER_VERSION", "tok-2")
    assert Bm25Index.build(corpus, params()).fingerprint != before


def test_no_hits_returns_empty() -> None:
    corpus = corpus_of(chunk("a", "derivative of a function"))
    index = Bm25Index.build(corpus, params())
    assert index.search("photosynthesis chlorophyll", 5, boost_section=None, roles=ALL) == []


def test_default_config_excludes_exercises_and_answer_keys() -> None:
    roles = load_help_config(DEFAULT_CONFIG_PATH).retrieval.roles
    assert "exercise" not in roles and "answer_key" not in roles


def test_real_corpus_smoke() -> None:
    corpus = load_corpus(REPO / "content" / "corpus" / "chunks.jsonl")
    cfg = load_help_config(DEFAULT_CONFIG_PATH).retrieval
    rss_before = rss_mb()
    start = time.perf_counter()
    index = Bm25Index.build(corpus, cfg)
    elapsed = time.perf_counter() - start
    roles = frozenset(ChunkRole(r) for r in cfg.roles)
    hits = index.search("chain rule derivative composite", 3, boost_section=None, roles=roles)
    print(f"build={elapsed:.3f}s rss_growth={rss_mb() - rss_before:.1f}MB")
    print("top3", [(h.chunk_id, round(h.score, 3)) for h in hits])
    assert elapsed < 2.0
    assert any(corpus.chunks[h.chunk_id].section == "3.6" for h in hits)
