# C1 review: evaluation and retrieval

[Review index](README.md) · [Validation](04-validation-and-next-steps.md)

## C1-R4 (P1): freeze dataset use, not only the commit

- Evidence: `src/mathtutor/help/eval/run.py:391-435`, especially both `meta.head == head`
  checks at lines 417 and 423. The same holdout becomes runnable after any new commit.
- Reproduction: `test_used_holdout_stays_used_after_new_commit` in
  [Python probes](test_review_probes.py), for both `run.json` and crash `started.json`.
  Synthetic previous metadata at `old` plus a clean mocked HEAD `new` passes `check_freeze`.
  Only the precondition helper is called; no actual holdout files or markers are used.
- This contradicts [spec 08](../../superpowers/specs/2026-10-26-milestone-c/08-evaluation-protocol.md):
  fixes after holdout results turn those cases into regression evidence. A fresh commit
  is not a fresh independent partition. The current documentation describes the weaker
  per-commit behavior, but the implementation must enforce the stronger dataset contract.
- Fix: persist partition identity and consumed status independently of code HEAD/run directory,
  including cases, retrieval queries and source problem/family membership. Acquire the
  started marker atomically so two runners cannot both pass preflight. Record code hashes
  as provenance, not as permission to reuse the partition. Keep regression runs distinct.
- Acceptance: new commits, output directories, crashes, reordered rows and simultaneous
  starts cannot restore eligibility. Rewording old cases is not an independent new set.
  Legacy markers without partition hashes require explicit conservative reconciliation.

## C1-R6 (P2): query the latest wrong attempt

- Evidence: `src/mathtutor/help/context.py:92-99` versus `retrieval/query.py:22-24`.
  Context intentionally stores the newest three attempts first; the query takes `wrong[-1]`.
  After two or three wrong submissions, feedback retrieves against the oldest retained one.
- Reproduction: `test_feedback_query_uses_latest_wrong_attempt`. Context assembled from
  `old_attempt`, then `latest_attempt`, produces a query containing only `old_attempt`.
- Fix: select the newest incorrect entry under the context's documented ordering, and
  make retrieval tests construct context through `assemble_context` rather than assuming
  an independent ordering. The misconception note already follows the latest attempt.
- Acceptance: one/two/three attempts, intervening non-incorrect outcomes and clipping/caps
  preserve the most recent applicable wrong answer. Verify production and evaluation agree.

## C1-R7 (P2): make the ablation measure a generator

- Evidence: `src/mathtutor/help/eval/run.py:70-85`, `help/pipeline.py:245-247`.
  `--no-retrieval` creates an empty corpus; the production pipeline immediately returns
  `abstained/no_hits`, so it never invokes the generator or produces raw model output.
- Reproduction: `test_no_retrieval_ablation_still_samples_model`: zero recorded requests,
  status `abstained`, reason `no_hits`, calls `[]` on an otherwise ordinary synthetic case.
- `evals/help/README.md` openly documents this behavior. It is a useful missing-source
  control, but does not fulfill the [fixed-generator comparison](../../superpowers/specs/2026-10-26-milestone-c/08-evaluation-protocol.md)
  between no retrieval and BM25. A zero-call comparison cannot establish retrieval benefit.
- Fix: give the evaluation-only baseline a defined no-passage prompt and citation policy,
  holding model, cases, output limits and guard fixed where meaningful. Label citation
  metrics that are inapplicable. Keep production's no-hit abstention intact.
  Alternatively explicitly defer the ablation and remove claims that this control satisfies it.
- Acceptance: an answerable baseline case calls the same generator; reports distinguish
  no-source fallback coverage from a generated no-retrieval baseline. Run on dev only.
