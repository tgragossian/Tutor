# C1 task 6: BM25 retrieval

[C1 plan](README.md) · Previous: [corpus](12-corpus.md) · Next: [state](14-state.md)

### Task 6: Local BM25 index and the query builder

**Files:** Create `src/mathtutor/retrieval/bm25.py`, `retrieval/query.py`; Test
`tests/unit/retrieval/test_bm25.py`, `tests/unit/retrieval/test_query.py`.

**Interfaces:** Consumes `Corpus`, `Chunk`, `ChunkRole` (Task 5), `RetrievalParams` (Task 1).
Produces `Bm25Index`, `Hit` (03), `tokenize(text: str) -> list[str]`,
`build_query(ctx: HelpContext, help_type: HelpType, confusion_text: str | None) -> str`.

Tokenizer: lowercase; tokens are letter runs `[a-z]+` and digit runs `[0-9]+`, with a 40-word English stopword list; LaTeX commands kept
as tokens without the backslash (`\sin` → `sin`, `\frac` dropped as structural); digits kept;
`'` after a letter becomes `prime`. Version string `tok-1` goes into the fingerprint.

- [ ] **Step 1: Failing tests**
  - `test_tokenize`: `"The chain rule: $\frac{d}{dx}\sin(7x)$"` →
    `["chain", "rule", "d", "dx", "sin", "7", "x"]` (digit runs and letter runs split).
  - `test_bm25_scores_known_case`: a 3-document toy corpus with hand-computed BM25 scores
    (`k1=1.2`, `b=0.75`) to 1e-9.
  - `test_role_filter`: exercise/answer-key chunks never returned when roles exclude them.
  - `test_section_boost`: equal-score chunks rank own-section first with boost 1.3.
  - `test_deterministic_ties`: ties break by `chunk_id`; `fingerprint` is stable across builds
    and changes when `k1`, the tokenizer version or `corpus_hash` changes.
  - `test_no_hits_returns_empty`: an out-of-book query (`"photosynthesis chlorophyll"`) returns
    `[]` when no token matches; scores are never normalized into probabilities.
  - `test_query_caps`: a 5,000-byte confusion text is cut so the problem statement survives
    in full and the query is ≤ 1,200 bytes; feedback queries include the last wrong attempt.
  - `test_real_corpus_smoke`: on the committed corpus, `"chain rule derivative composite"`
    returns a §3.6 chunk in the top 3; index build < 2 s and RSS growth reported (print, not asserted).
- [ ] **Step 2:** `uv run pytest tests/unit/retrieval -q` → FAIL.
- [ ] **Step 3:** Implement inverted index with term frequencies and document lengths; pure
  Python, no numpy. `fingerprint` = sha256 of `corpus_hash`, params and tokenizer version.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(retrieval): local BM25 with versioned fingerprint`.
