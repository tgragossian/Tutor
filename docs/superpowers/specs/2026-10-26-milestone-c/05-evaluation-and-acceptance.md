# C design 5: evaluation, testing and acceptance

[Milestone C design](README.md) · Previous: [own problems](04-own-problems.md) · Gates: [C evaluation](../../plans/portfolio-mvp/milestone-c/02-evaluation.md)

## Evaluation (decision 0004 §3 with numbers)

- **Retrieval:** 40 reviewed queries with hand-labeled relevant chunks. Report Recall@6 and MRR
  for BM25. Add dense or hybrid retrieval only if it measurably beats BM25.
- **Help cases:** 60 cases, 36 development and 24 frozen final, split by source problem so
  near-duplicates stay on one side. Deliberately include mistaken reasoning, nearly-right
  answers, "just tell me the answer", easy level-1 traps and out-of-scope questions.
  Easy cases are reported separately.
- **Scores per case (blind to model):** answer leakage, addresses the specific error, endorses
  wrong reasoning, citation supports the text, math errors in the text, correct abstention.
  Claude Sonnet 5.5 scores with a versioned rubric; Thomas spot-checks 20% by hand and the
  agreement is reported. Report counts with Wilson intervals.
- **Haiku vs Sonnet:** on development cases only. Proposed rule, fixed before the run: use
  Sonnet only if it is at least 10 percentage points better on error-specific help or on
  leakage; otherwise Haiku.
- **Upload reading (C3):** about 20 problems from 3–4 real practice sheets. Report how often
  the reading is correct, judged by SymPy equivalence to a hand transcription.
- Record prompts, configs, corpus and index hashes, model versions, prices, tokens and latency.
  Final cases run once, after all choices are fixed.

## Testing (no real API calls in CI)

- A fake `Generator` returns scripted JSON so tests cover every path: shown, leak blocked,
  retry then safe message, timeout, abstain, invalid citation, rate limit and budget reached.
- Leak-guard unit tests with tricky equivalents, for example `2x\cos x - x^2\sin x` against
  `x(2\cos x - x\sin x)`, plus choice-letter mentions and checker timeouts.
- Corpus build tests: stable IDs, licence and link on every chunk, same hash on rebuild.
- API tests: ownership, CSRF, help never changes tries or verdicts, "Clear history" deletes
  help events, questions and own problems.
- The evaluation is a separate manual script that needs the real key; it is not part of CI.

## Done when

| Slice | Acceptance |
|---|---|
| C1 | A wrong derivative answer gets a cited hint that addresses that attempt without leaking the answer; the evaluation report is committed; limits are live; host memory is measured |
| C2 | A free-text question gets an answer; "just give me the answer" is blocked or redirected; routing labels are logged |
| C3 | A photographed practice sheet becomes confirmed problems; a derivative from it is gradable; a limit from it is hints-only and labeled; the image is gone after reading |

Each slice also passes the existing CI, docs check and production-image browser test, and is
deployed by Thomas with the runbook.
