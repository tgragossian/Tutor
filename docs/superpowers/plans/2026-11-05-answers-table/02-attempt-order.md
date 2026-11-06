# Task 2: One attempt order

[Plan](README.md) · Spec D8

**Files:**
- Modify: `src/mathtutor/help/context.py:46-49` (`AttemptLine`), `:88-111`
  (`assemble_context`), `:172-199` (`build_context`)
- Modify: `src/mathtutor/retrieval/query.py:20-25`, `src/mathtutor/help/prompts.py:130-147`
- Modify: `src/mathtutor/help/eval/run.py:150-160` (builds `AttemptLine` from case files)
- Test: `tests/unit/help/test_context.py`, `tests/unit/retrieval/test_query.py`,
  `tests/unit/help/test_prompts.py`

**Interfaces:**
- Consumes: `applied_answers(db, session_item_id) -> list[Answer]` (Task 1).
- Produces: `AttemptLine(latex: str, status: VerdictStatus, attempt_no: int)`.
  `HelpContext.attempts`: oldest → newest, at most `MAX_ATTEMPTS` (3) most recent; the
  latest is `attempts[-1]`. No caller reverses it.

- [ ] **Step 1: Capture the current prompt.** Before changing code, add
  `test_attempts_block_unchanged` to `test_prompts.py`: build the user prompt for a context
  with three attempts (incorrect, unable_to_verify, incorrect) and assert it equals a
  literal string pasted from the current output. Run it; it passes now and must stay passing.
- [ ] **Step 2: Write failing tests.**
  `test_context.py::test_attempts_oldest_to_newest_with_numbers`: five applied answers give
  `[a.attempt_no for a in ctx.attempts] == [3, 4, 5]` and `ctx.attempts[-1]` is the latest.
  `test_query.py::test_feedback_query_uses_latest_wrong_attempt`: attempts
  `[(x, incorrect, 1), (y, incorrect, 2), (z, correct, 3)]`; the query contains `y`, not `x`.
- [ ] **Step 3:** Run both; expected FAIL (`attempt_no` missing; order reversed).
- [ ] **Step 4: Implement.** `assemble_context` keeps `attempts[-MAX_ATTEMPTS:]` without
  `reversed`; `build_context` maps `Answer` → `AttemptLine` (choice answers use the choice's
  LaTeX, as now). `query.py` takes the latest wrong with `reversed(ctx.attempts)`.
  `prompts.py` drops its `reversed` and keeps the same labels ("Earlier attempt i",
  "LATEST attempt"). `eval/run.py` numbers case attempts 1..n. Update the comments at
  `query.py:22`, `prompts.py:133-135` and the `assemble_context` docstring to the single order.
- [ ] **Step 5:** Run the full check; expected all pass, including Step 1's golden test.
- [ ] **Step 6: Commit** `refactor(help): one oldest-to-newest attempt order with attempt_no`.
