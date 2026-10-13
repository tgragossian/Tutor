# Project structure recommendation

[Review index](README.md)

The proposed src layout and pure math/recommendation packages are good.
Add one application layer so session transactions are shared by HTML and JSON routes.
The original web/flow.py would otherwise accumulate persistence and session rules.

## Target tree, created only as each milestone needs it

```text
src/mathtutor/
  domain.py              Shared records/enums; no framework imports
  content/               Reviewed problem and source schemas/loaders
  verify/                Allowlist, domain checks, checkers, bounded workers
  application/           Submit, advance, reveal, hint use cases
  store/                 SQLAlchemy models, repositories and transactions
  web/                   FastAPI routes, DTOs, auth, templates and assets
  ingest/                Offline HTML parsing and reviewed-content promotion
  retrieval/             Corpus/chunks, BM25, later dense/hybrid experiments
  tutor/                 Prompt construction, provider calls, citation validation
  recommend/             Add only after the static baseline works
content/
  sources/               Source manifests, URLs, licensing, hashes
  problems/              Human-reviewed problem records
evals/
  verifier/              Human cases, generated regressions, results
  retrieval/             Queries, relevance labels, results
  tutor/                 Dialogue cases, rubrics, blinded scores
experiments/             Configs and concise reports; LoRA only when started
tests/
  unit/
  integration/
  e2e/
tools/                   MathLive capture and explicit batch entry points
migrations/
deploy/
docs/                    Linked short documents
```

Use evals/ consistently if this proposal is accepted; the old plan uses eval/.
Do not pre-create empty packages or abstractions for every future experiment.
For the MVP, one small recommend module is enough; no policy framework is necessary.

## Dependency rules

- web -> application; both HTML and JSON adapters invoke the same use cases.
- application -> content, verify, store; later tutor and recommendation.
- verify never imports web, store, an LLM client or application.
- retrieval ranks passages; tutor generates hints; neither decides grade correctness.
- ingest produces candidate artifacts offline; review promotes them into served content.
- domain contains durable records, not HTTP or ORM types.
- Config and dependency construction belong at app startup, not global import time.

Use request-scoped database sessions and a single bounded worker pool per app process.
Version content and evaluation artifacts independently of database migrations.
Keep large downloads, indexes, checkpoints and runtime SQLite files out of Git.
Commit small reviewed fixtures, experiment configurations and reproducible result summaries.
Preserve original code/content licensing in vendored and derived assets.

## Documentation maintenance

Keep original plans under their existing Superpowers roots.
Use one file per substantial responsibility or task; split before reaching 100 lines.
Store long machine-readable results in JSON/CSV, with a short linked Markdown report.
Future CI should check Markdown line counts and internal links, not required headings.
Do not add assistant coauthor trailers; acknowledge Claude/Codex in the README footnote.
