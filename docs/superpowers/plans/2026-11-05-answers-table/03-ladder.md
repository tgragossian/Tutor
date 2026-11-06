# Task 3: Ladder by mistakes, answer link, five tries

[Plan](README.md) · Spec D4, D6, D6a, D7, D9, D10

**Files:**
- Create: `migrations/versions/0007_mistake_ladder.py`
- Modify: `src/mathtutor/store/models.py` (`ItemHelpState`, `HelpRequestRow`)
- Modify: `src/mathtutor/help/service.py:148-179` (`HintPlan`, `_hint_plan`), `_Admitted`
  (`:132-145`), `availability` (`:259-276`), `_admit` (`:369-436`), `_build_context`
  (`:323-333`), `_advance_ladder` (`:594-622`)
- Modify: `src/mathtutor/domain.py:7` (`MAX_TRIES = 5`)
- Test: `tests/unit/help/test_service.py`, `tests/unit/store/test_migrations.py`,
  `tests/unit/application/test_practice.py`, `tests/integration/test_help_api.py`,
  `tools/e2e/smoke.mjs` (tries text)

**Interfaces:**
- Consumes: `latest_wrong`, `mistake_counts`, `set_mistake_type` (Task 1).
- Produces: `_hint_plan(start_hints: int, latest: Answer | None, counts: dict[str, int])
  -> HintPlan` (same `HintPlan` fields). `HelpRequestRow.answer_id: int | None` (FK
  `answers.id`). `_Admitted.answer_id: int | None` replaces `latest_wrong` and `ladder`.

- [ ] **Step 1: Write failing ladder tests** in `test_service.py` (pure `_hint_plan`):
  `test_no_wrong_answer_first_hint_is_level_0_step_1` (start_hints 0 → level 0, step 1);
  `test_no_wrong_answer_later_hints_are_try_again` (start_hints 1 and 5 →
  `HintPlan.try_again is True`);
  `test_second_hint_on_same_wrong_answer_is_try_again` (a delivered hint already names this
  `answer_id` → `try_again is True`);
  `test_first_wrong_rule_is_level_1` (latest typed `wrong_rule`, counts `{"wrong_rule": 1}` → 1);
  `test_second_and_fourth_same_type_are_2_and_3` (counts 2 → 2; counts 4 → 3);
  `test_other_type_starts_at_1` (latest `algebra`, counts `{"wrong_rule": 2, "algebra": 1}` → 1);
  `test_unlabeled_offers_counts_plus_one` (latest untyped, counts `{"wrong_rule": 2}` →
  `levels == {"algebra": 1, "wrong_rule": 3, "rule_misapplied": 1, "incomplete": 1}`).
- [ ] **Step 2: Write failing service tests:**
  `test_repeat_hint_same_attempt_returns_fixed_message` (second Hint on one wrong answer:
  status `try_again`, the after-answer D6a text exactly, no ledger entry, no generator call);
  `test_classifying_hint_labels_answer` (untyped latest → after delivery `answers.mistake_type`
  equals the scripted type and `help_requests.answer_id` is that answer);
  `test_classifying_hint_keeps_existing_label` (label set between admission and finalize →
  unchanged; `help_requests.mistake_type` still records the type the hint used);
  `test_help_without_wrong_answer_has_no_answer_id`;
  `test_second_hint_before_attempt_returns_fixed_message` (status `try_again`, the
  no-attempt D6a text exactly, no ledger entry, no generator call, `start_hints` unchanged;
  a wrong answer afterwards gets a normal level-1 hint);
  `test_explain_and_feedback_not_limited` (repeat Explain this / What did I do wrong? still
  call the model as today).
- [ ] **Step 3:** Run them; expected FAIL.
- [ ] **Step 4: Migration 0007** (`down_revision="0006"`): add `help_requests.answer_id`
  (Integer, FK `answers.id`, nullable); drop `item_help_state.hint_attempt_pk`, `hint_type`,
  `hint_counts`, `hint_level`. Downgrade re-adds them with 0005's types and defaults.
  Test `test_0007_round_trip` in `test_migrations.py`.
- [ ] **Step 5: Implement.** `_admit` reads `latest_wrong` and `mistake_counts` for the item,
  stores `answer_id` on the row and on `_Admitted`. `_advance_ladder` writes
  `row.hint_level` / `row.mistake_type`, counts level-0 hints in `start_hints`, and for a
  classifying hint calls `set_mistake_type(db, admitted.answer_id, kind)`; it no longer
  touches counters. `availability` uses the same `_hint_plan` inputs. Delete `_type_level`.
  `HintPlan` gains `try_again: bool = False`: true when a delivered hint row already exists
  for this item with the same `answer_id` (NULL before any attempt). `HelpStatus` gains
  `TRY_AGAIN` (`"try_again"`); `help/messages.py` gains `TRY_FIRST` and `TRY_AGAIN` with the
  D6a texts. `_admit` answers it before the ledger: a `help_requests` row with that status,
  no calls, no reservation, `help_seq` advanced. The web client shows it like other fixed
  messages.
  Update the R35 docstrings (models, service header, migration docstring) to the new rule.
- [ ] **Step 6: Five tries.** `MAX_TRIES = 5`; update tests that exhaust an item after 3 wrong
  answers, and the "Tries left" expectations in `tools/e2e/smoke.mjs`.
- [ ] **Step 7:** Run the full check plus `npm test --prefix tools`. Expected: all pass.
- [ ] **Step 8: Commit** `feat(help): hint ladder climbs by mistakes made; five tries
  (migration 0007)`.
