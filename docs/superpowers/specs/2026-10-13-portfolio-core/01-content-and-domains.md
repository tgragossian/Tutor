# 01 — Content and domains

[Contracts index](README.md)

## Authoring and compilation

- Authors write problems in YAML under `content/problems/`, with answers in **LaTeX**.
- A build step, `tools/compile_content` (Node + the pinned Compute Engine), parses each answer with the **same** non-canonical parser the browser uses.
- The output is committed to `content/compiled/problems.json`.
- The server loads **only** the compiled file and translates expected answers with the same allowlisted translator used for students (see [03](03-input-bounds.md)).
- This gives one parser for everything and no `parse_expr`. LLM-extracted content from the later pipeline flows through the same path.
- CI recompiles and fails if the committed output is out of date.

## Problem record (authored YAML)

```yaml
id: openstax-c1-3.6-221
topic: derivatives.chain_rule
difficulty: 2                      # 1–5 rubric (reference design §4.3)
source: {book: "OpenStax Calculus Volume 1", section: "3.6", exercise: 221,
         url: "https://openstax.org/books/calculus-volume-1/pages/3-6-the-chain-rule",
         license: "CC BY-NC-SA 4.0"}
statement: "Find $\\frac{dy}{dx}$ for $y = \\sin(3x^2)$."
answer:
  kind: expression                 # expression | numeric | choice
  latex: "6x\\cos(3x^2)"
  variable: x
  domain: {intervals: [["-inf", "inf", "open", "open"]], exclude: []}
  strict_domain: false
misconceptions: ["cos(3x^2)  # missing inner derivative"]   # optional, for eval and RAG
review: {status: human_verified, reviewer: "tg", date: 2026-10-20, notes: ""}
```

## Domain

- `domain.intervals` is a list of `[lo, hi, lo_kind, hi_kind]`. The kinds are `open` or `closed`, and the bounds are rationals, `-inf` or `inf`.
- `domain.exclude` lists isolated points that are excluded.
- **The domain is mathematical, not a sampling range.** It is the set on which the answer is assessed.
- **Default** (`strict_domain: false`): equivalence holds on the domain, ignoring **provably removable** holes ([04](04-equivalence.md)).
- **`strict_domain: true`:** the student's expression must also be defined at every point of the domain. Use this when a problem assesses definedness itself.
- The author must declare the domain of the expected answer. Example: for d/dx √x the answer 1/(2√x) has domain `(0, inf)`.
- The loader checks that the expected answer is defined on the declared domain, using the same constraint check as [04](04-equivalence.md). An unprovable domain is a content error.

## `numeric` and `choice` extras

- `numeric`: `latex` is the exact value. `precision: {decimals: 3}` or `precision: exact` (see [02](02-answer-contracts.md)).
- `choice`: `choices: [{id: a, latex: "..."}, ...]` and `correct: b`. Choice ids match `^[a-z]$`.

## Review status

- `human_verified` is the only status served in milestones A and B.
- `needs_review` is loaded but never served.
- The pipeline's `auto_verified` and `computed_only` statuses are defined with the extraction stage. `computed_only` is never served as a reliable graded assessment.

## Versioning

- `content_version` for an item = the first 12 hex characters of the SHA-256 of its canonical compiled JSON.
- Topics carry a stable `topic_id`. A renamed topic keeps its id.
- Attempts store `content_version`, so historical attempts can still be interpreted after content changes.

## Loader errors (abort startup and fail CI)

The loader stops on any of:
- a schema error, duplicate id or unknown topic
- an uncompiled or stale answer
- the expected answer failing the translator
- the expected answer not proven equal to itself
- an expected answer whose domain cannot be proven
- `choices` given for a non-`choice` kind, or a missing `correct` id
