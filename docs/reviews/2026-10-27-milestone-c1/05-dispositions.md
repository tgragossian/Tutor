# C1 review: fix dispositions and Codex verdicts

[Review index](README.md) · [Validation](04-validation-and-next-steps.md) · [Handoff](../../../handoff.md)

Claude recorded the fixes below on 2026-10-27. Codex rechecked `b16a206` on 2026-10-28:
R1/R2/R3/R5/R6/R8/R9 closed first; R4/R7 reopened, then [closed by local fixes](11-debugging-fixes.md).
[Recheck](07-recheck.md) records intermediate verdicts; [debugging fixes](11-debugging-fixes.md) owns final evidence.
The table preserves fix provenance; a fixing commit alone does not establish closure.

| ID | Fix | Regression tests | Deviation or limit |
|---|---|---|---|
| C1-R1 | `38c2de4` | `tests/unit/test_dockerfile.py` (every data path set and copied; help loads from the rebuilt `/app` layout); smoke checks the files in the image | No Docker here: the real image test is the smoke run (owner step) |
| C1-R2 | `63c280c` | `test_answer_plus_canceling_foreign_terms_is_blocked` (7 shapes) and the numeric variant, safe notation still passes (real checker, `test_guard_pool.py`); unit tests in `test_leak_guard.py` | See D1 |
| C1-R3 | `e9aa144` | `test_unexpected_generator_crash_keeps_reservation_uncertain`, `test_reply_decode_error_retains_spend_reservation`, `test_repair_call_crash_keeps_only_that_call_uncertain`, `test_prompt_budget_failure_before_dispatch_settles_zero`; generator `bad_response` tests | Restart persistence is the ledger's existing durable row; not retested here |
| C1-R4 | `005adab` | `test_eval_spend_holdout.py`: new commit, reordered/reworded, shared chunks, lock, 8-way race; `test_unclaimed_holdout_marker_blocks_every_commit`; `test_holdout_claim_written_before_the_first_provider_call` | See D2 |
| C1-R5 | `08c4b60` | `test_pipeline_does_not_deliver_after_guard_overruns` (+ in-time control), `test_clearance_after_the_deadline_is_unchecked` | Post-check only: no hard response-time bound, as Codex noted |
| C1-R6 | `3a87d68` | `test_feedback_queries_the_latest_wrong_attempt` (6 cases via `assemble_context`) | None |
| C1-R7 | `005adab` | `test_no_retrieval_baseline_calls_the_same_generator_without_passages`, `..._rejects_invented_citations_and_still_guards`, `test_production_prompt_has_no_baseline_addendum` | See D3 |
| C1-R8 | `9bde1d9` | `help_panel.test.mjs`: lost response, unreadable body, 502, double pending, other tab's pending, type change, item change, definitive 429 | Two real tabs not tested in a browser |
| C1-R9 | `005adab` | `test_eval_spend_holdout.py`: open reservation, torn line, interrupt mid-call and mid-judge, interrupted `_execute` + `--spent`, run id reuse | See D4 |

## Deviations from the review's suggested fix

- **D1 (R2).** Codex suggested blocking unresolved foreign composites outright. Instead each
  foreign symbol of any shape and each function application (`f(x)`, identical ones shared)
  is one atom, substituted like single letters (variable, 0, each alone; 1 on numeric) and
  every variant goes to the checker; more than three atoms block. Nothing foreign passes
  without checker verdicts, while `f'(g(x))\,g'(x)` or `\frac{dy}{dx}` hints stay usable.
  The review probe's fake pool answers "no match" to everything, so it cannot tell the two
  designs apart; the real-checker tests above are the evidence.
- **D2 (R4).** The claim covers case, problem, query and relevant-chunk ids, so a new
  holdout needs new problems and new relevant passages. There is no regression-run mode:
  a used holdout simply cannot run again through this runner.
- **D3 (R7).** The baseline keeps the production prompt and adds the eval-only
  `prompts/v1/no_passages.md` (answer from own knowledge, no citations). Same model, limits,
  repair and guard; citation measures are labeled not applicable in the summary.
- **D4 (R9).** The durable record is `results/<run_id>/spend.jsonl` (fsynced reserve before
  each help/judge call, settle after), not an early `run.json`. The review probe asserts
  `run.json` after an interrupt and will keep failing by design; `--spent` replaces summing
  `run.json` files. Provider-side reconciliation is still manual (console).

## Codex decisions on deviations

- **D1 / R31 accepted for the reported bypass:** all variants reach the checker; the real
  integration tests cover cancellation and safe notation. This bounded heuristic is not
  certified inequality for every original foreign expression; retain that limitation.
- **D2 / R32 completed locally:** durable claims now precede scores; retrieval-only is
  refused for holdout. [R4 fix and regression evidence](11-debugging-fixes.md).
- **D3 / R33 completed locally:** recorded mode preserves uncited replies through judging,
  audit and recompute. [R7 fix and regression evidence](11-debugging-fixes.md).
- **D4 / R34 accepted:** the durable journal, not `run.json`, owns spend recovery.
  `--spent` must drive remaining-credit calculations; provider reconciliation is manual.

Original review probes are retired navigation stubs. Saved R4/R7 follow-up probes pass;
regressions are in the normal test tree. See [close-out](06-codex-closeout.md).
