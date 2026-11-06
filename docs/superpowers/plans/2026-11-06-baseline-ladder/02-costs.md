# Task 2: Cost and compute columns

[Plan](README.md) · Spec: cost and compute

**Files:**
- Modify: `src/mathtutor/help/eval/report.py` (summary columns, comparison table),
  `src/mathtutor/help/eval/run.py` (record guard CPU ms per response)
- Test: `tests/unit/help/test_eval_report.py`

**Interfaces — Produces:**
- `Summary.cost_per_useful_usd: float | None` (total USD / useful count; None when 0 useful).
- `Summary.guard_ms_p50`, `Summary.guard_ms_p95: int | None`.
- `compare(runs: list[RunData]) -> str`: one Markdown table, one row per arm, columns in this
  order: arm, leaks per case, leaks per delivered, useful, math errors, guard blocked
  (arm 3 only) or would block (arms 1–2), cost per hint, cost per useful hint, p95 latency,
  guard p95 ms.
- Classifier cost line for arm 3: wrong answers in the run × the recorded Haiku mean cost
  from `usage_entries` tariffs (stated as an estimate when not measured in the run).

- [ ] **Step 1: Failing tests:** `test_cost_per_useful_divides_total_by_useful`,
  `test_cost_per_useful_none_when_nothing_useful`, `test_compare_rows_in_arm_order`,
  `test_leaks_per_delivered_excludes_abstentions`, `test_guard_ms_recorded`.
- [ ] **Step 2:** Run them; expected FAIL.
- [ ] **Step 3: Implement.** Reuse `Measure` for rates; keep existing summary fields.
- [ ] **Step 4:** Full check. Expected: all pass; old summaries render unchanged.
- [ ] **Step 5: Commit** `feat(eval): cost per useful hint, guard time and arm comparison`.
