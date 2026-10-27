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
