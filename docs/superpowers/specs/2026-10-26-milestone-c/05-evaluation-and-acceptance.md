# C design 5: evaluation, testing and acceptance

[Milestone C design](README.md) · Previous: [own problems](04-own-problems.md) · Gates: [C evaluation](../../plans/portfolio-mvp/milestone-c/02-evaluation.md)

## Evaluation (decision 0004 §3 with numbers)

Review amendment: [evaluation protocol](08-evaluation-protocol.md) owns exact partition and
metric semantics. C-P2 must fix numerical release gates before the paid comparison.

- **Retrieval:** 40 reviewed queries across the book with relevant chunks. Report Recall@6 and MRR@6
  for BM25. Add dense or hybrid retrieval only if it measurably beats BM25.
- **Help cases:** 60 cases, 36 development and 24 frozen C release holdout, split by problem/family so
  near-duplicates stay on one side. Deliberately include mistaken reasoning, nearly-right
  answers, "just tell me the answer", easy level-1 traps and out-of-scope questions.
  Easy cases are reported separately.
- **Scores per case (blind to model):** answer leakage, addresses the specific error, endorses
  wrong reasoning, citation supports the text, math errors in the text, correct abstention.
  Claude Sonnet 5.5 scores with a versioned rubric; Thomas checks a stratified random 20%
  plus flagged failures/disagreements. Report raw and delivered scores, useful coverage,
  marginal Wilson intervals and paired/family-aware uncertainty separately.
- **Haiku vs Sonnet:** on development cases only. Proposed rule, fixed before the run: use
  Sonnet needs a 10-point gain on a predeclared primary measure AND must satisfy safety and
  useful-coverage gates; resolve the measure/tolerances in C-P2. Neither ships if both fail.
- **Upload reading (C3):** about 20 problems from 3–4 real practice sheets. Report how often
  the reading is correct against a human transcription, including task/variable/domain;
  equivalence of a formula alone is insufficient.
- Record prompts, configs, corpus and index hashes, model versions, prices, tokens and latency.
  C release cases run after choices are fixed; reserve a separate untouched LoRA/E final set.

## Testing (no real API calls in CI)

- A fake `Generator` returns scripted JSON so tests cover every path: shown, leak blocked,
  retry then safe message, timeout, abstain, invalid citation, rate limit and budget reached.
- Leak-guard unit tests with tricky equivalents, for example `2x\cos x - x^2\sin x` against
  `x(2\cos x - x\sin x)`, plus choice-letter mentions and checker timeouts.
- Corpus build tests: stable IDs, licence and link on every chunk, same hash on rebuild.
- API tests: ownership, CSRF, help never changes tries or verdicts, "Clear history" deletes
  help events, questions and own problems.
- Lifecycle tests: duplicate/conflicting IDs, stale results, deletion during inference,
  durable budget reservations/restart/month rollover and no unchecked streaming/rendering.
- Mixed-load checks: help/retries/intake do not starve grading or exceed the measured memory budget.
- The evaluation is a separate manual script that needs the real key; it is not part of CI.

## Done when

| Slice | Acceptance |
|---|---|
| C1 | C-P1/C-P2 resolved; useful cited hint demo plus abstention; quality gates/report, race-safe limits and mixed-load/memory evidence |
| C2 | A free-text question gets an answer; "just give me the answer" is blocked or redirected; routing labels are logged |
| C3 | C-P3 resolved; confirmed supported derivative is gradable, a limit is hints-only; bounded intake, privacy and local cleanup verified |

Each slice also passes the existing CI, docs check and production-image browser test, and is
deployed by Thomas with the runbook.
The demo alone is not acceptance: report leakage/endorsement/math-error and citation/coverage
gates from C-P2, with denominators and intervals. A safe-message-only system must not pass.
