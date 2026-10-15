# Portfolio core: technical contracts (milestones A–B)

[Specs index](../README.md) · [Handoff](../../../../handoff.md) · [Decision 0001](../../../decisions/0001-delivery-verifier-attribution.md) · [Delivery plan](../../plans/portfolio-mvp/README.md)

**Status:** approved by Thomas on 2026-10-13. Milestone A skeleton is live; the
practice loop and verifier contracts remain for milestone B.

**What this replaces:** the [reference design](../2026-10-13-core-practice-loop-design.md), for milestones A and B (deployed skeleton + three-topic practice loop). Where the two conflict, this spec wins.

**What takes precedence over this spec:** decision 0001.

**Not covered here:**
- RAG hints (milestone C) get their own spec.
- Each item in the expansion queue gets its own spec when its turn comes.

## Scope

- **Topics:** `derivatives.basic_rules`, `derivatives.trig`, `derivatives.chain_rule` (OpenStax Vol. 1 §3.3, §3.5, §3.6).
- **Content:**
  - 6 reviewed seed problems in milestone A
  - 20–30 reviewed problems by the end of milestone B
- **Answer kinds:** `expression`, `numeric`, `choice`.
  - `antiderivative`, `limit`, `point_set` and `implicit_derivative` are deferred to topic expansion.
  - Their contracts are noted in [02](02-answer-contracts.md) and decision 0001.
- **Session mode:** one practice mode only.
  - Problems come in textbook order. Unseen problems first, then ones answered incorrectly.
  - Retry, reveal, skip and advance are all supported.
- **Accounts and history:**
  - Users, durable item presentations, submissions and results.
  - Enough history to evaluate a later selection policy.
- **UI:** MathLive with the calculus button row plus the built-in keyboard (approved mockup). Source attribution is shown on every problem.
- **Deployment:** Docker + HTTPS skeleton in milestone A, and a public demo at the end of milestone B.

## Modules

| # | Module | Answers the question |
|---|---|---|
| 01 | [Content and domains](01-content-and-domains.md) | What does a problem record contain, and what is its mathematical domain? |
| 02 | [Answer contracts](02-answer-contracts.md) | What does the browser submit, and how is precision handled? |
| 03 | [Input bounds and translation](03-input-bounds.md) | What input is accepted before any math runs? |
| 04 | [Equivalence and domains](04-equivalence.md) | When is an answer correct, incorrect, or unverifiable? |
| 05 | [Verifier execution](05-verifier-execution.md) | Where and how long does math run, and what happens on failure? |
| 06 | [Session state](06-session-state.md) | Presentations, submissions, retries, idempotency |
| 07 | [Application and web](07-application-and-web.md) | Services, routes, DTOs, auth, security |
| 08 | [Verifier evaluation](08-verifier-evaluation.md) | Datasets, splits, metrics, release gates |
| 09 | [Operations](09-operations.md) | Host sizing, releases, backups, costs |

## Cross-cutting rules

- Student input and any machine-generated content are **untrusted**. Neither ever reaches `eval`, `sympify` or `parse_expr`.
- "Correct" requires a **proof** within a supported family of expressions. Numeric probes may only **refute** an answer.
- `unable_to_verify` is never shown or counted as wrong, and never traps a student on an item.
- Every result records the content, verifier and evaluation versions it came from, so it can be reproduced.
- Markdown files: ≤ 100 lines, linked from a parent index.
- No AI co-author trailers on commits; see the README acknowledgments.
