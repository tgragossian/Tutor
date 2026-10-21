# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-21 after tasks 10–14 on `milestone-b` (not pushed).
Milestone B work continues in the `milestone-b` worktree: `.claude/worktrees/milestone-b`.

## Current state

- 2026-10-21: tasks 10–14 complete on `milestone-b` (d865179..c52305d): store, accounts,
  practice service, JSON API, pages with MathLive. 839 Python and 19 Node tests pass; a real
  browser run typed `18x(3x^2+1)^2` and got "Correct" with no CSP violations. Task 15's smoke
  script and e2e CI job are in 5fd8952. [Rulings A1–A18](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md).
- Milestone B tasks 1–9 are complete and merged to `main`; tasks 10–16 are not started.
  The bounded SymPy verifier and reviewed evaluation are on `main`.
- R24 was implemented with tests first in a76985d; problem 253 now says
  “Give an exact answer or round to 3 decimal places.”
- b5ad4b2 recaptured all 136 reviewed cases (`tg`), matching source: 49 correct,
  50 incorrect, 37 unsupported, including `d-sqsq-02`'s `[0, inf)` domain.
- e995438 records the passing non-draft [release result](evals/verifier/results/dev-b.json)
  at verifier `0.1.0+b5ad4b2`. 8a0bb40 enables the reviewed dev gate in CI.
- [CI run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416) is green
  for Python, Node and container smoke after d673400 fixed Linux pool-test cleanup.
  Thomas reports 722 Linux tests passed, including the memory-limit test.
- Merged to `main` in 102a22f (handoff conflict resolved for milestone-b); the merged tree equals
  milestone-b. [CI run 39506433419](https://github.com/tgragossian/Tutor/actions/runs/39506433419)
  on `main` is green (Python incl. reviewed dev gate, Node, container smoke). The web process
  still does not import SymPy (R8).
- Live site, probed 2026-10-20 after the merge: `/healthz` 200, `/readyz` 200. The host still runs
  milestone A; it has not pulled `main`. The practice loop, accounts and UI remain unfinished.

## Next action: task 15 content, then task 16

1. Thomas: choose how to source 14–24 new problems (OpenStax's no-LLM-ingestion notice blocks
   fetching the book): transcribe statements yourself, use Claude-written `adapted` items, or both.
2. Draft, check, review (gate), commit; then task 16 (Docker volume, migrations, memory, deploy).
3. Known: CI's `container` job fails `/readyz` until task 16. See the
   [execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md).

## Reviewed evidence

- FA **0 of 50** (95% Wilson upper bound **7.1%**); FR **0 of 49** (upper bound **7.3%**).
- Coverage **49/49**; unsupported graded correct **0 of 37** (upper bound **9.4%**);
  agreement **136/136**; internal errors **0**.
- Seven cases return `wrong_decimal_places` as labelled. These are reviewed dev results;
  the held-out final evaluation remains a later milestone.
- [Results and CI evidence](evals/verifier/results/README.md) records versions and provenance.
  `dev-draft.json` is historical, not the release result. Resume claims use the reviewed 0/50.
- Prior CI failures were test teardown, not failed mathematical assertions. d673400 removes
  the test's competing worker reap. FA 0 and containment remain unchanged.
- Node 20/Ubuntu GitHub deprecation notices are warnings. Linux CI passes; production host
  sizing and practice-browser checks still belong to later release work.

## R24 scope

- Numeric problems explicitly requesting N places require exactly N on standalone decimals.
  Exact fractions/expressions remain allowed; other lengths are format issues, not incorrect.
- LaTeX preserves trailing zeros; disagreement with MathJSON abstains. No universal decimal
  cap or coefficient rounding: decimals inside expressions remain exact rationals.
- [Decision 0001](docs/decisions/0001-delivery-verifier-attribution.md) still governs holes:
  ignore only provably removable holes by default; `strict_domain` applies to domain/range
  problems, including undefined nested denominators such as `1/tan`.

## Navigation and working rules

- [Documentation](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B tasks](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md),
  [R24 checklist/debugging](docs/superpowers/plans/portfolio-mvp/milestone-b/r24/README.md),
  [contracts](docs/superpowers/specs/2026-10-13-portfolio-core/README.md), [follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md).
- Tasks 12–14 still need atomic revisions, replay responses, 422 kind checks and friendly
  format messages. Task 15 adds reviewed content; task 16 owns host sizing/deployment.
- Never relax FA 0 or containment. Record actual hours in [hours](docs/ops/hours.md);
  resolve scope/date/contingency with Thomas at the 30-hour checkpoint.
- Markdown files stay ≤100 lines, split by responsibility and linked from a parent index.
  No assistant co-author trailers; acknowledge assistance in [README](README.md#acknowledgments).
  Describe the verifier as proof-based/SymPy; do not call the tutor LLM-based.
- Preserve [original references](docs/handoff/README.md) and dated [reviews](docs/reviews/README.md).
  Option B continues with practice, evaluated RAG hints, operations/final evaluation, then
  the [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md).
