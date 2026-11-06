# Answers table: controller rulings and deferred minors

[Brief](README.md)

Rulings were made during the build without stopping for Thomas; each lists what it costs if
wrong. Deferred minors come from the per-task reviews; the final review triaged them.

## Rulings

- **R1** `_hint_plan(start_hints, latest, counts, hinted=False)`: `hinted` = a delivered hint
  row exists with `answer_id == latest.id`; no-attempt case uses `start_hints >= 1`. Cost if
  wrong: a signature rename.
- **R2** `try_again` text is the no-attempt text when the help row's `answer_id` is NULL and
  the after-answer text otherwise, chosen where fixed messages render. Cost: a lookup refactor.
- **R3** Focused tests while iterating; the full check once before each task's last commit.
  Cost: an intermediate commit could be red.
- **R4** `npm ci --prefix tools` before `npm test` in the worktree. Cost: install time.
- **R5** `answers.mathjson` is a Text-backed JSON type (SQLite gives a `JSON` column NUMERIC
  affinity, which turned `10**20+1` into `1e+20`); the global `json_deserializer` change was
  reverted. Cost: one column type swap.
- **R6** Downgrade renumbers `attempt_results.id` (nothing references it). Cost: an
  old-schema reader keyed on result ids.
- **R7** Added service-level `attempt_no` tests (second answer = 2; `unable_to_verify`
  numbered, no try). Cost: one extra test.
- **R8** Accepted the golden prompt test as captured from pre-change output. Cost: prompt drift,
  caught by the next paid dev run.
- **R9** Merged local `main` (README fine-tuning section) into the branch before Task 5's
  README edits. Cost: one merge commit.

## Deferred minors (per-task reviews)

- T1: migration test readability; `ItemHelpState` docstring (rewritten in Task 3).
- T2: RED evidence was a signature error, not an order failure; one near-duplicate query
  test; no `build_context` test for choice problems or fewer than 3 attempts.
- T3: clear history keeps the one-hint lock (see 02); `try_again` wording on an exhausted item
  (see 02); the message replaces the hint on screen (see 02); `try_again` rows are not
  throttled by the ledger; a guard needs a comment.
- T4: classifier files hashed into the hint `prompt_id`, classifier prompt id not recorded;
  one rate-limit test assertion proves nothing; `security.md` quotes only the first sentence
  of the notice; classify over-reserves at the help worst case (~2,300 µ$ vs ~55); choice
  branch and settle-failure path untested.
- T5: `docs/ops/runbook-c1.md` is exactly 100 lines; one README bullet wraps unevenly.

- **R10** Final fix wave: two stale debugging-doc lines, and the deploy section moved from
  `runbook-c1.md` to `docs/ops/runbook-answers-table.md` with container smoke and a migrate
  rehearsal on a backup copy. Cost: one extra doc file.
- **R11 (Thomas)** No merge of this branch and no work on the baseline-ladder plan before
  Codex review.

## Final review (Claude, whole branch)

Verdict: ready to merge with fixes; no Critical or Important findings. Pre-merge fixes are
R10. Every deferred minor above was triaged "can wait"; T3/T4 user-facing ones went to
[02-open-decisions.md](02-open-decisions.md). Also raised there: no per-user cap on classifier
calls, and `try_again` wording after a later `unable_to_verify` answer. Not run: Haiku 5.5
with `effort: "low"` and structured output (needs a paid call); container e2e (no Docker).
