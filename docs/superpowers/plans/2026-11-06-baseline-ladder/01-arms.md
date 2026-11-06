# Task 1: Arms in the runner

[Plan](README.md) · Spec: arms 1–2, fairness rules

**Files:**
- Modify: `src/mathtutor/help/eval/run.py` (CLI `--arm {full,plain,pasted}`, mutually
  exclusive with `--no-retrieval`; run metadata `arm`), `src/mathtutor/help/eval/judge.py`
  (free-text records), `src/mathtutor/help/eval/report.py` (arm label, N/A columns)
- Create: `src/mathtutor/help/eval/arms.py` (prompt builders and the measure-only call),
  `src/mathtutor/help/prompts/eval/plain.md`, `src/mathtutor/help/prompts/eval/pasted.md`
- Test: `tests/unit/help/test_eval_arms.py` (new), `tests/unit/help/test_eval_report.py`

**Interfaces — Produces:**
- `build_plain_request(case, problem) -> GenerationRequest` (no system prompt; plain-text
  schema-free reply) and `build_pasted_request(case, problem, cfg) -> GenerationRequest`.
- `run_arm_case(case, env, arm) -> CaseRecord` with `CaseRecord.arm: str` and
  `CaseRecord.guard_would_block: bool | None`; delivered text is the raw reply.

- [ ] **Step 1: Failing tests:** `test_plain_request_has_no_system_prompt`,
  `test_plain_request_phrasing_per_help_type`, `test_pasted_request_contains_production_rules_verbatim`,
  `test_arm_delivers_raw_text_even_when_guard_would_block` (fake generator returns the
  reference answer → delivered text unchanged, `guard_would_block is True`),
  `test_arm_records_reach_judge_items`, `test_old_run_without_arm_loads_as_full`,
  `test_arm_and_no_retrieval_are_mutually_exclusive`.
- [ ] **Step 2:** Run them; expected FAIL.
- [ ] **Step 3: Implement** with the existing generator, ledger and spend journal (same
  `--max-usd` protection). The production `HelpPipeline` is not called for new arms.
- [ ] **Step 4:** Full check (ruff, format, mypy, pytest). Expected: all pass.
- [ ] **Step 5: Commit** `feat(eval): plain and pasted baseline arms (measure-only guard)`.
