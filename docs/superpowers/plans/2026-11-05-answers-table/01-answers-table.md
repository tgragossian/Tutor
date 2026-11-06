# Task 1: Answers table

[Plan](README.md) · Spec D1–D3

**Files:**
- Modify: `src/mathtutor/store/models.py:142-181` (replace `Submission`, `AttemptResult`)
- Create: `migrations/versions/0006_answers.py`, `src/mathtutor/store/answers.py`
- Modify: `src/mathtutor/application/practice.py` (`_encode/_decode_answer`, `_untouched_session`,
  `session_summary`, `_replay`, `_claim`, `_reserve`, `_grade`, `_release`, `_history`)
- Modify: `src/mathtutor/help/context.py:172-199`, `src/mathtutor/help/service.py:657-682`
- Test: `tests/unit/store/test_answers.py` (new), `tests/unit/store/test_migrations.py`,
  `tests/unit/store/test_models.py`, `tests/unit/application/test_practice.py`,
  `test_recovery.py`, `tests/integration/test_submit_races.py`, and any other test the grep
  `Submission\b|AttemptResult` finds

**Interfaces — Produces:**
- `class Answer(Base)`, table `answers`: `id` int PK; `submission_id` str(36) unique;
  `user_id` FK `users.id`; `session_item_id` FK `session_items.id`; `attempt_no` int NULL;
  `answer_kind` AnswerKind; `mathjson` JSON NULL; `choice_id` str(64) NULL; `latex` Text NULL;
  `created_at`; `reserved_revision` int NULL; `lease` int default 0; `leased_at` NULL;
  NULL until graded: `status` VerdictStatus, `reason` VerdictReason, `method` Method,
  `verifier_version` str(64), `worker_ms`, `queue_ms`, `seconds_on_item` int,
  `counts_as_try` bool, `applied` bool; `mistake_type` str(16) NULL.
  `UniqueConstraint("session_item_id", "attempt_no", name="uq_answers_item_attempt")`,
  `Index("ix_answers_session_item_id", "session_item_id")`,
  `Index("ix_answers_user_id_mistake_type", "user_id", "mistake_type")`.
  `SessionItem.answers` relationship ordered by `Answer.id` (replaces `.submissions`).
- `store/answers.py` (every answer query lives here):
  `applied_answers(db, session_item_id: int) -> list[Answer]` (applied, by `attempt_no`);
  `latest_applied(db, session_item_id: int) -> Answer | None`;
  `latest_wrong(db, session_item_id: int) -> Answer | None`;
  `next_attempt_no(db, session_item_id: int) -> int` (max + 1, starting at 1);
  `mistake_counts(db, session_item_id: int) -> dict[str, int]` (applied incorrect, typed);
  `set_mistake_type(db, answer_id: int, mistake_type: str) -> bool` (write-once; True if
  written; only for an applied incorrect answer).

- [ ] **Step 1: Write failing tests** in `tests/unit/store/test_answers.py`:
  `test_applied_answers_in_attempt_order`, `test_latest_wrong_skips_correct_and_unapplied`,
  `test_next_attempt_no_starts_at_1_and_skips_unapplied`,
  `test_attempt_no_unique_per_item` (second insert with the same pair raises `IntegrityError`),
  `test_set_mistake_type_is_write_once` (`True` then `False`, value unchanged),
  `test_set_mistake_type_refuses_correct_answer` (returns `False`),
  `test_mistake_counts_ignores_unlabeled`.
- [ ] **Step 2:** Run `uv run pytest tests/unit/store/test_answers.py -q`. Expected: import error.
- [ ] **Step 3: Model and helpers.** Replace the two classes with `Answer`; write the helpers.
- [ ] **Step 4: Migration 0006** (`down_revision="0005"`). Upgrade: create `answers`; copy in
  Python over `op.get_bind()` rows of `submissions LEFT JOIN attempt_results`, joined to
  `session_items` → `study_sessions` for `user_id`; split `answer_json` into `mathjson` and
  `choice_id`; `attempt_no` = 1, 2, … per item over applied rows in `submissions.id` order;
  `mistake_type` = `item_help_state.hint_type` where `hint_attempt_pk` is this row and it is
  applied incorrect; drop `attempt_results`, then `submissions`. Downgrade rebuilds both old
  tables from `answers` (`answer_json` = `{"mathjson": …, "choice_id": …}`) and drops `answers`.
  Tests in `test_migrations.py`: `test_0006_copies_answers_with_attempt_numbers` seeds an
  applied incorrect, an applied correct, an unapplied result, an orphan (no result) and a NULL
  `reserved_revision` row, then asserts every column, `attempt_no` 1, 2, NULL, NULL, and
  `mistake_type` from `hint_type`; `test_0006_downgrade_round_trip` compares old rows.
- [ ] **Step 5: Callers.** Replace every `Submission`/`AttemptResult` use: "ungraded" becomes
  `Answer.status IS NULL` (lease claim and `_release` filters); `_grade` writes the verdict
  with `UPDATE answers … WHERE id = ? AND status IS NULL`. Zero rows means a concurrent
  regrade won, which takes the old `IntegrityError` replay path. When applied, set
  `attempt_no = next_attempt_no(...)` in the same transaction. `_reserve` sets `user_id`.
  `build_context`, `_latest_status`, `_latest_wrong`, `session_summary` and `_history` use
  `store/answers.py` or `Answer` columns; `context.py:192` reads `choice_id` directly.
- [ ] **Step 6: Race test** in `test_submit_races.py`:
  `test_concurrent_answers_get_distinct_attempt_numbers` (two answers on one item; one
  applies as `attempt_no` 1; the other is stale with `attempt_no` NULL).
- [ ] **Step 7:** Run the full check from Global Constraints. Expected: all pass. Behavior is
  unchanged, so existing practice and help tests pass after the renames alone.
- [ ] **Step 8: Commit** `refactor(store): one answers row per attempt with user_id and
  attempt_no (migration 0006)`.
