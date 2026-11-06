# Answers table: design (Thomas, 2026-11-05)

[Plan](README.md)

## Problem

- One answer is split across `submissions` (what was typed) and `attempt_results` (verdict),
  1:1. Part of the answer is a JSON string in a text column (`answer_json`), parsed by readers.
- `submissions` has no `user_id`; ownership needs answer → item → session → user.
- Attempt order is implied by row id, and help flips the list three times (`context.py:100`,
  `query.py:22`, `prompts.py:135`). That mix-up caused ruling R40 (help coached an older try).
- The mistake label lives in one overwritable slot (`item_help_state.hint_attempt_pk` /
  `hint_type`), and only the latest wrong attempt is ever labeled, so per-type counts are wrong.

## Decisions

- **D1 One row per answer.** New table `answers` replaces `submissions` and `attempt_results`.
  Ids are preserved (`answers.id` = old `submissions.id`). Verdict columns are NULL until graded.
- **D2 Plain columns.** `mathjson` (JSON) and `choice_id` (string) replace `answer_json`;
  `latex` replaces `answer_latex`. Add `user_id` (FK `users.id`).
- **D3 `attempt_no`.** 1-based per `session_item_id`, set in the grading transaction only when
  the result is applied. Counts every applied graded answer (correct, incorrect,
  unable_to_verify); `counts_as_try` says which used a try. NULL while ungraded or not applied.
  Unique `(session_item_id, attempt_no)`. Format issues and busy releases still delete the
  reserved row (unchanged), so they never get a number. Help clicks never create answer rows.
- **D4 `mistake_type`.** NULL unless the answer is applied and incorrect. Otherwise one of
  `MISTAKE_TYPES` (`algebra`, `wrong_rule`, `rule_misapplied`, `incomplete`). Write-once: the
  first writer wins (background classifier or a classifying hint) and it is never overwritten.
- **D5 Classify every wrong answer, in the background.** After an applied incorrect verdict,
  one worker thread asks Claude Haiku 5.5 (effort low) for the type. Ledger `kind="classify"`,
  inside the monthly cap, not counted against per-user help limits, never retried. A failure
  or refusal leaves NULL; the classifying hint then labels it (D4). Off when help is off.
- **D6 The ladder climbs by mistakes made** (replaces R35's count of hints given). For type T,
  level = min(applied incorrect answers on this presentation with type T, 3). The latest wrong
  answer's type sets the level; if it has no type yet, the classifying hint is offered
  {t: min(count_t + 1, 3)}.
- **D6a One hint per attempt.** Before any attempt, the first Hint gives the level-0 hint
  (step 1, a question about the problem's form); after each wrong answer, the first Hint gives
  that answer's level. Any further Hint click on the same state returns a fixed message with
  no model call (status `try_again`). No attempt yet: "You've already had a hint for getting
  started. Try an answer, even a partial one, and I can help with what you wrote. If a step
  is unclear, use Explain this." After a wrong answer: "You've already had a hint for this
  answer. Try again with it in mind, and I can help with what you change. If the method is
  unclear, use Explain this." Why (Thomas): a student who lacks the concept uses Explain
  this; one who knows the direction but finds the problem hard climbs the ladder by trying.
  Level-0 step 2 (naming the rule) is no longer served; its eval cases stay as pipeline
  regression cases. What did I do wrong? and Explain this are unchanged.
- **D7 Five tries.** `MAX_TRIES` 3 → 5, so the higher levels are reachable.
- **D8 One attempt order.** Oldest → newest everywhere; `AttemptLine` carries `attempt_no`;
  the latest is last. The prompt text the model sees stays byte-identical.
- **D9 `help_requests.answer_id`.** The latest applied wrong answer at admission (NULL when
  none). Old rows stay NULL; `next_submission_id` is unchanged.
- **D10 `item_help_state` slims down.** Drop `hint_attempt_pk`, `hint_type`, `hint_counts`,
  `hint_level`; keep `start_hints`, `help_seq`, `in_flight`.
- **D11 Privacy copy.** Answers now go to Anthropic on a wrong answer, not only on help:
  update the practice page notice and `docs/ops/security.md` (US spelling).
- **D12 Not deployed by this plan.** Merge to `main` after CI; deploy later after a fresh DB
  backup and Codex review. Measured C1 results used 3 tries and the hint-count ladder.

## Out of scope

Moving the recovery lease columns to their own table; removing `SessionItem.tries_used` (the
grading guard relies on it); keeping malformed answers; showing real attempt numbers in the
prompt; changing `next_submission_id`.
