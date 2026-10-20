# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-20 against `milestone-b` d673400.
Keep this worktree's handoff when merging: `.claude/worktrees/milestone-b/handoff.md`.

## Current state

- Milestone B tasks 1–9 are complete on `milestone-b`; tasks 10–16 are not started.
  The bounded SymPy verifier and reviewed evaluation have landed on this branch.
- R24 was implemented with tests first in a76985d; problem 253 now says
  “Give an exact answer or round to 3 decimal places.”
- b5ad4b2 recaptured all 136 reviewed cases (`tg`), matching source: 49 correct,
  50 incorrect, 37 unsupported, including `d-sqsq-02`'s `[0, inf)` domain.
- e995438 records the passing non-draft [release result](evals/verifier/results/dev-b.json)
  at verifier `0.1.0+b5ad4b2`. 8a0bb40 enables the reviewed dev gate in CI.
- [CI run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416) is green
  for Python, Node and container smoke after d673400 fixed Linux pool-test cleanup.
  Thomas reports 722 Linux tests passed, including the memory-limit test.
- `main` still contains milestone A. The verifier track is ready for Thomas's merge;
  the practice loop, accounts and UI remain unfinished. No B deployment is claimed.

## Next action: Thomas's merge

1. Commit/push this documentation update and retain the required green checks.
2. Thomas merges tasks 1–9 to `main`, keeping this milestone-b `handoff.md`.
3. Thomas confirms the live site's health/readiness checks still pass. The last
   [host record](docs/ops/host.md) serves the skeleton; this docs pass did not probe it.
4. Update branch/merge status after that confirmation. Continue tasks 10–16 separately;
   merging the verifier does not complete or deploy the full practice application.

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
