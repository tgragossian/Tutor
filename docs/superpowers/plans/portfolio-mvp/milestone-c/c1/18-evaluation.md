# C1 task 14: evaluation harness, cases and the paid run

[C1 plan](README.md) · [Gates](02-gates.md) · Previous: [UI](17-ui.md) · Next: [release](19-release.md)

### Task 14: Cases, judging, gates and the report

**Files:** Create `src/mathtutor/help/eval/{__init__,cases,run,judge,gates,report}.py`,
`evals/help/cases/{dev,holdout}.jsonl`, `evals/help/retrieval/{dev,holdout}.jsonl`,
`evals/help/rubric/v1.md`, `evals/help/README.md`; results go to `evals/help/results/<run_id>/`
(`results.jsonl` git-ignored, `summary.md` ≤100 lines committed); Test `tests/unit/help/test_eval_*.py`.

**Interfaces:** Consumes `HelpService` internals through one function
`run_case(case: HelpCase, generator: Generator, model: str) -> CaseRecord` that builds the same
context/prompt/guard path as production with a synthetic session item (no database user).
`CaseRecord` keeps every raw call output and the delivered result, so raw and delivered
scores are reported separately (spec 08). `--no-retrieval` runs the same cases with no passages.
`HelpCase(case_id, split, problem_id, help_type, attempts: list[str], confusion_id | None,
hint_level, tags: set[str], expect_abstain: bool)`. `RetrievalQuery(query_id, split, text,
relevant_ids: list[str])`. `gates.evaluate(summary) -> list[GateResult(name, value, threshold, passed)]`
encodes [02-gates](02-gates.md) exactly; `wilson(k, n) -> tuple[float, float]`.

- [ ] **Step 1: Failing tests:** `test_splits_grouped_by_problem` (no `problem_id` in both
  splits; holdout covers 3 topics, ≥ 7 problems), `test_case_mix_matches_gates`,
  `test_runner_refuses_holdout_without_freeze` (needs `--freeze <commit>` and a clean tree),
  `test_runner_never_reads_final`, `test_wilson_known_values` (k=0,n=24 → upper ≈ 0.138),
  `test_gates_always_abstain_fails` (a synthetic all-abstain summary fails useful coverage),
  `test_gates_selection_rule` (Sonnet +9 pp → Haiku; +10 pp but one gate 6 pp worse → Haiku),
  `test_judge_blind` (judge prompt has no model id; order shuffled with a recorded seed),
  `test_spend_cap` (`--max-usd 8` stops the run before exceeding it, using the same tariff).
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS. Commit
  `feat(eval): help evaluation harness and gates`.
- [ ] **Step 5 (drafting, Claude):** Draft 60 help cases and 40 retrieval queries per the
  case mix in 02, citing chunk IDs from the committed corpus; mark each `needs_review`.
- [ ] **Step 6 (owner, Thomas):** Review every case and retrieval label; edit or drop; set
  `reviewed_by: tg`. The runner refuses unreviewed cases. Commit the reviewed sets.
- [ ] **Step 7 (paid, Thomas runs with his key):** `uv run python -m mathtutor.help.eval.run
  --split dev --models claude-haiku-5-5,claude-sonnet-5-5 --max-usd 8`, plus one Haiku
  `--no-retrieval` dev run as the retrieval baseline. Iterate prompts on dev only; record each run. Apply the selection rule; write the chosen model into `help_config.json`.
- [ ] **Step 8 (owner):** Thomas audits the stratified 20% and every flagged case in the
  generated `audit.csv`; the runner recomputes with his labels.
- [ ] **Step 9 (paid, once):** `--split holdout --freeze <commit>` with the chosen model.
  Commit `summary.md` with denominators, intervals, gate table, prices and corpus/index hashes.
  A failing gate blocks release (Task 15) and turns those cases into regression evidence.
- [ ] **Step 10:** Commit `docs(eval): C1 evaluation results`.

Budget note: Anthropic console spend limit must cover the app budget plus planned eval spend
during the evaluation month (for example $25), with auto-reload off.
