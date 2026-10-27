# Corpus snapshot: OpenStax Calculus Volume 1

Source: https://openstax.org/books/calculus-volume-1/ (CC BY-NC-SA 4.0, (c) OpenStax).
Used only as retrieval text so hints can cite the textbook; attribution goes in the app README.

## Probe findings (2026-10-26)

- Book and section pages (`/books/calculus-volume-1/pages/<slug>`) are a client-rendered
  shell: about 238 KB of HTML with no section math and no TeX. Not usable as a source.
- `/rex/release.json` names the current archive (`archiveUrl`, e.g.
  `/apps/archive/20260604.144757`) and each book's `defaultVersion` (here `8dbc2ce`).
- Archive JSON on the same host works with plain `urllib`:
  - Book tree: `<archive>/contents/<book-uuid>@<version>.json` (`tree.contents`, nested).
  - One page: `<archive>/contents/<book-uuid>@<version>:<page-uuid>.json`, whose `content`
    field is the page's HTML (and `abstract`, `title`, `slug`).
  - A bare `<page-uuid>.json` returns the site's 404 shell; the book-qualified id is required.
- Math is MathML only: `<math><semantics><mrow>...</mrow><annotation-xml
  encoding="MathML-Content">...`. There is NO `<annotation encoding="application/x-tex">`.
  Task 5 must convert presentation MathML (the `<semantics>` first child) to text/LaTeX.
- Book UUID: `8b89d172-2927-466f-8661-01abc7ccdba4`. Host is `openstax.org` only; no other host.

## Decision

`source_kind = "archive_json"`. Raw pages are stored as the received JSON bytes
(`data/corpus-raw/<edition>/<slug>.json`, git-ignored), not `.html`; extract `content` in Task 5.
`edition` is `calculus-volume-1@<version>`.

## Tool

`uv run python tools/corpus/fetch.py --out data/corpus-raw` resolves the current archive and
version from `release.json`, fetches the tree and every leaf page, and writes
`content/corpus/snapshot.json` atomically only if all pages arrived. Any failure exits non-zero
and writes no manifest. A run first deletes any existing `snapshot.json`, so a failed run
never leaves a stale manifest next to partly re-fetched raw files. Pin a re-run with `--archive-path` and `--version`.

Rules: HTTPS `openstax.org` only (redirects are checked too), one request per second, up to 3
attempts per URL, User-Agent `mathtutor-corpus/1 (+https://tutor.thomasgragossian.dev)`.

## Manifest

`snapshot.json`: `edition`, `base_url`, `fetched_at`, `source_kind`, `fetch_tool_version`, and
`toc` (book order) with `slug`, `section`, `title`, `kind`, `url`, `sha256`, `bytes`.

Conventions: `section` is `N.M` for numbered sections, `N.intro` for chapter openers,
`N.<name>` for composite pages (slug `N-<name>`), `Appendix X`, and `answer-key.<slug>`.

`kind` labels each page so Task 5 can include or exclude it:

- `numbered-section` (45): the teaching text; `section` is `1.1` through `6.9`.
- `intro` (6): chapter openers. `composite-page` (24): per-chapter Key Terms, Key Equations,
  Key Concepts, Review Exercises (`section` like `3.key-terms`).
- `preface` (1), `index` (1), `appendix` (3: A Table of Integrals, B Table of Derivatives,
  C Review of Pre-Calculus).
- `answer-key` (6): one per chapter. These contain worked answers to textbook exercises, so
  they must not be indexed as hint-citable text without an explicit decision.

Fixtures for the tests live in `tests/fixtures/corpus/` (trimmed tree and one trimmed page).

## Chunks (Task 5)

`uv run python tools/corpus/build.py` verifies each raw page against `snapshot.json`, converts
MathML with `mathtutor.retrieval.mathml` (`$...$` inline, `$$...$$` display) and writes
`chunks.jsonl` + `manifest.json`. Same snapshot, same bytes; `corpus_hash` is the SHA-256 of
`chunks.jsonl`, `snapshot_sha256` hashes the snapshot without `fetched_at`.
`load_corpus` refuses a corpus whose hashes, count, edition or licence do not match.

IDs are `c1-<section>-<kind><n>[-p<k>]`, numbered per section and kind in book order:
`txt` prose under one heading, `def`/`thm`/`rule` boxes (problem-solving strategies are
`rule`), `ex` examples, `exr` checkpoints, student projects and exercise lists, `key` answers
(role `answer_key`, filed under the exercise's section). Chapter pages use section `N.0`
(key terms `def`, key equations `rule`, review exercises `exr`); key concepts go to the
section they summarize. Chapter openers, preface, appendices, index, media boxes, images and
alt text are not chunked. Target 300-500 estimated tokens (`ceil(utf8_bytes/3)`), ceiling
700. Longer boxes split into `-p1`, `-p2`, each repeating the title; a display equation stays
with its lead-in sentence and a lower-case continuation ("where ..."). Exception: gluing
never crosses a box boundary. When the lead-in sits before a box (c1-3.7-thm3, whose six
displays follow "...provided in the following theorem." in the previous `txt` chunk), the
box chunk starts with its title and displays only. Prose `$` is escaped as `\$`, so unescaped
`$` only delimits math.

Build of `8dbc2ce`: 1,765 chunks (explanation 595, exercise 495, example 357, answer_key 112,
definition 80, theorem 72, rule 54); 18,058 math elements, `unavailable_math` 0 (one more
formula sits in a skipped media box); 95 answers/exercises that were only an image are dropped.
`chunks.jsonl` is about 1.9 MB.

Math rendering notes (read c1-1.2-txt3, c1-1.3-rule1, c1-1.5-ex3, c1-3.5-txt2, c1-3.6-rule1,
c1-3.9-ex2, c1-5.1-txt4, c1-5.3-thm1, c1-5.5-ex2):

- Correct and readable: fractions, limits, integrals with bounds, sigma sums, primes, roots,
  piecewise (`cases`), dollar amounts (`\$500`).
- Multi-line derivations become `\begin{array}{rl...}` with empty spacer columns and the
  book's step notes as `\text{ Simplify.}`; some start with an empty row.
- Inner thin spaces survive (`\sin\,\theta`, `2z\:dz`); leading/trailing ones are dropped.
- `min`/`max`/`sec` after a value with no argument are units (`5\:\text{ sec }`).
- An evaluation bar is `\left. ... \right|_{x = a}` (`\Big|_{a}^{b}` with no left operand).
- A comma between two numbers stays unspaced (`1,502.08`, `[0,100]`): the MathML does not
  say whether it is a thousands separator.
- Equation numbers follow the display as plain text: `$$...$$ (3.17)`.
- Some lead-in sentences ("...given in the following rule.") form tiny `txt` chunks.
