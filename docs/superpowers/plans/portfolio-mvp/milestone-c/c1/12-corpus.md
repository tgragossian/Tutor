# C1 tasks 4–5: corpus snapshot and build

[C1 plan](README.md) · [Corpus contract](../../../../specs/2026-10-26-milestone-c/07-corpus-contract.md) · Next: [retrieval](13-retrieval.md)

### Task 4: Acquire a frozen snapshot of the whole book

**Files:** Create `tools/corpus/fetch.py`, `content/corpus/README.md`, `content/corpus/snapshot.json`;
Modify `.gitignore` (add `data/corpus-raw/`); Test `tests/unit/corpus/test_fetch.py`.

**Interfaces:** Produces raw pages at `data/corpus-raw/<edition>/<slug>.html` (git-ignored) and the
committed `content/corpus/snapshot.json`: `{edition, base_url, fetched_at, source_kind,
toc: [{slug, section, title, url, sha256, bytes}], fetch_tool_version}`.

- [ ] **Step 1: Probe the source (no code kept).** Fetch the book's first page and one section
  page with `curl`; record in `content/corpus/README.md` whether section HTML is in the served
  page or in an archive JSON endpoint it references, and whether math carries a TeX annotation
  (`<annotation encoding="application/x-tex">`) or MathML only. This choice sets `source_kind`
  (`page_html` or `archive_json`) and Task 5's math path. Stop and tell Thomas if neither works.
- [ ] **Step 2: Failing tests** with saved fixture pages in `tests/fixtures/corpus/`:
  `test_toc_complete` (TOC parser returns every chapter's sections from the fixture, in order),
  `test_snapshot_records_hashes`, `test_incomplete_fetch_fails` (a missing page makes the tool exit
  non-zero and write no `snapshot.json`), `test_https_openstax_only` (other hosts rejected).
- [ ] **Step 3:** Implement: stdlib `urllib` + `html.parser`; 1 request/second; User-Agent
  `mathtutor-corpus/1 (+https://tutor.thomasgragossian.dev)`; HTTPS `openstax.org` only; writes atomically.
- [ ] **Step 4:** Tests PASS. Run once for real: `uv run python tools/corpus/fetch.py --out data/corpus-raw`
  and commit `snapshot.json` (every TOC section present, Appendices/answer keys recorded but labeled).
- [ ] **Step 5:** Commit `feat(corpus): reproducible whole-book snapshot manifest`.

### Task 5: Build chunks and the corpus manifest

**Files:** Create `tools/corpus/build.py`, `src/mathtutor/retrieval/__init__.py`,
`retrieval/corpus.py`, `retrieval/mathml.py` (only if Task 4 found MathML without TeX);
Output `content/corpus/chunks.jsonl`, `content/corpus/manifest.json`; Test `tests/unit/corpus/test_build.py`,
`tests/unit/retrieval/test_corpus.py`.

**Interfaces:** Produces `Chunk`, `ChunkRole`, `Corpus`, `load_corpus` (03). `manifest.json`:
`{edition, snapshot_sha256, build_version, normalizer, chunk_count, role_counts, section_counts,
unavailable_math: int, corpus_hash, licence: "CC BY-NC-SA 4.0"}`.

- [ ] **Step 1: Failing tests** on the fixture snapshot:
  - `test_ids_stable_and_unique`: IDs match `^c1-\d+\.\d+-(def|thm|rule|ex|txt|exr|key)\d+(-p\d+)?$`; no collisions.
  - `test_rebuild_identical`: two builds give byte-identical `chunks.jsonl` and the same `corpus_hash`.
  - `test_every_chunk_has_url_and_licence`: canonical `https://openstax.org/books/calculus-volume-1/pages/...#anchor`.
  - `test_math_kept_as_latex`: a fixture equation appears as `$...$` LaTeX in chunk text.
  - `test_long_example_split_with_context`: an example over the ceiling becomes `-p1`, `-p2`, each
    starting with the example title; no chunk exceeds 700 estimated tokens.
  - `test_exercises_labeled`: exercise lists and answer keys get `exercise`/`answer_key` roles.
  - `test_changed_text_changes_hash`: editing one paragraph changes that chunk's `content_hash`
    and `corpus_hash` but not its ID.
  - `test_load_corpus_rejects_bad_hash`: `load_corpus` verifies `corpus_hash` against the file.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: NFC + whitespace normalization; target 300–500 tokens; never split
  an equation from the sentence stating its conditions; sort by (chapter, section, document order).
  `corpus_hash` = sha256 of the canonical JSONL. Fetch timestamps are excluded from hashed content.
- [ ] **Step 4:** Tests PASS. Build the real corpus, commit `chunks.jsonl` + `manifest.json`;
  read 3 chunks each from chapters 1, 3, 5 and note math rendering issues in `content/corpus/README.md`.
  Add `content/corpus` to the Docker image (Dockerfile `COPY`).
- [ ] **Step 5:** Commit `feat(corpus): deterministic whole-book chunks with provenance`.
