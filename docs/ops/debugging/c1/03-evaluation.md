# C1: evaluation debugging

[C1 debugging](README.md) · [Evaluation guide](../../../../evals/help/README.md) ·
[Fixed defects](../../../reviews/2026-10-27-milestone-c1/11-debugging-fixes.md)

Paths below are relative to `src/mathtutor/help/eval/`. C1-R4/R7 now have passing regressions.
Use temporary synthetic cases/claims to investigate them; never run the real holdout as a probe.

| Symptom | Owning module and evidence |
|---|---|
| Holdout reuse is accepted | `run.py`, `holdout.py`: every metric-producing branch must check/claim partition use before output (R4) |
| Baseline delivered but unjudged | `judge.py::judge_items`: check recorded `no_passages` mode through raw item -> judgment -> audit -> recompute (R7) |
| Interrupted run seems free | `spend.py`: reserve precedes dispatch and is fsynced; open reservation counts at worst case (R9) |
| Credit calculation disagrees | `run.py --spent` includes all spend journals, not only completed `run.json` summaries |
| Citation metrics look misleading | `report.py`: distinguish membership/support, raw/delivered results, baseline not-applicable denominators |
| Model-selection/gate mismatch | `gates.py`, `report.py`: predeclared thresholds, primary metric, coverage and all-delivered-judged gate |
| Hint outcome not reproducible | `cases.py`, `run.py`: `expect_mistake_type`, `prior_hints`, `start_step`, prompt fingerprint and case versions |

## Focused offline checks

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/help/test_eval_spend_holdout.py tests/unit/help/test_eval_judge.py tests/unit/help/test_eval_report.py -q
.venv\Scripts\python.exe -m pytest docs/reviews/2026-10-27-milestone-c1/test_recheck_probes.py -q --tb=short
```

Both commands now pass. The follow-up probes have no xfails; stronger regressions live in
the normal test tree. Original pre-fix probes are retired navigation stubs; their original
implementations remain in git. Retrieval-only is dev-only; holdout claims precede scoring.

Persist run IDs, partition claims, spend journals, prompt/config/corpus versions and
safe failure reasons. Keep raw help in the existing ignored evaluation artifacts only.
Never delete a holdout claim or reuse a run ID to obtain a fresh-looking release result.
An outputless/crashed run can still consume credit and the holdout partition.
