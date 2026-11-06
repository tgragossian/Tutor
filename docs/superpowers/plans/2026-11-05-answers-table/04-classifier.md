# Task 4: Background mistake classifier

[Plan](README.md) · Spec D5, D11

**Files:**
- Create: `src/mathtutor/help/classify.py`, `src/mathtutor/help/prompts/v1/classify.md`
- Modify: `src/mathtutor/help/help_config.json`, `src/mathtutor/help/config.py`
- Modify: `src/mathtutor/application/practice.py` (`PracticeService.__init__`, `_grade`)
- Modify: `src/mathtutor/web/app.py:200-290` (build, attach and close the classifier)
- Modify: `src/mathtutor/web/templates/practice.html:42`, `docs/ops/security.md:41`
- Test: `tests/unit/help/test_classify.py` (new), `tests/unit/application/test_practice.py`

**Interfaces:**
- Consumes: `Answer`, `set_mistake_type` (Task 1); `Ledger.admit(db, user_id, request_id,
  model, *, kind)`, `settle`, `mark_uncertain`; `Generator`, `GenerationRequest`,
  `GeneratorError`, `MISTAKE_TYPES`, `MISTAKE_DESCRIPTIONS` (existing).
- Produces:
  - `ClassifierParams(model: str, effort: str, max_output_tokens: int, timeout_s: float,
    queue_max: int)`; config key `"classifier": {"model": "claude-haiku-5-5", "effort": "low",
    "max_output_tokens": 200, "timeout_s": 10.0, "queue_max": 32}`.
  - `CLASSIFY_SCHEMA`: object with one required `mistake_type` string, enum `MISTAKE_TYPES`,
    `additionalProperties: false`.
  - `class MistakeClassifier(sessions, cfg: HelpConfig, ledger: Ledger, generator: Generator,
    problem_of: Callable[[SessionItem], Problem])` with `classify(answer_id: int) -> str | None`
    (synchronous), `submit(answer_id: int) -> None` (one worker thread; drops when
    `queue_max` tasks are waiting) and `close() -> None`.
  - `PracticeService(..., on_wrong: Callable[[int], None] | None = None)`: called with the
    answer id after the grading transaction commits, only for an applied incorrect verdict.
    Exceptions are caught and logged by type only; the student's reply never waits on it.

- [ ] **Step 1: Write failing tests** in `test_classify.py` (fake generator and real ledger):
  `test_labels_wrong_answer` (fake returns `{"mistake_type": "wrong_rule"}` → stored);
  `test_skips_correct_unapplied_or_labeled` (no generator call);
  `test_one_call_per_answer` (second `classify` makes no call; ledger `request_id` is
  `f"classify-{answer_id}"`, `kind == "classify"`);
  `test_budget_spent_makes_no_call` (month cap reached → `None`, no call, NULL kept);
  `test_classify_outside_help_rate_limit` (user at the hourly help limit is still classified,
  and classify entries do not count toward that limit);
  `test_provider_error_leaves_null` (`GeneratorError` → `None`; billed-unknown →
  `mark_uncertain`);
  `test_bad_reply_leaves_null` (enum violation → `None`, call settled);
  `test_queue_full_drops` (`queue_max=1`, blocked worker, third `submit` dropped);
  `test_prompt_marks_student_text` (attempt LaTeX only inside `<student_text>`).
  In `test_practice.py`: `test_on_wrong_called_once_for_applied_incorrect` and
  `test_on_wrong_not_called_for_correct_or_stale`; `test_on_wrong_error_does_not_fail_submit`.
- [ ] **Step 2:** Run them; expected FAIL (module missing).
- [ ] **Step 3: Implement.** Prompt: `classify.md` states the four types with
  `MISTAKE_DESCRIPTIONS`; the user message carries the statement, the reference answer (the
  model returns only a label, so nothing reaches the student) and the attempt inside
  `<student_text>`, reusing `prompts.py`'s escaping. Reserve in the ledger, call, then settle
  in the existing order. Never log student text or model output.
- [ ] **Step 4: Wire.** `app.py` builds the classifier only when help is enabled and passes
  `classifier.submit` as `on_wrong`; shutdown calls `close()` before the pools close.
- [ ] **Step 5: Privacy copy** (`practice.html:42`): "When you submit a wrong answer or ask
  for help, the problem and your recent answers are sent to Anthropic's Claude to sort the
  mistake and write the hint. Anthropic keeps API data for a limited time under its standard
  policy. We save the help text with your practice history and delete it when you clear your
  history." Update `security.md:41` to match.
- [ ] **Step 6:** Run the full check. Expected: all pass, with no network calls.
- [ ] **Step 7: Commit** `feat(help): label every wrong answer in the background with Haiku`.
