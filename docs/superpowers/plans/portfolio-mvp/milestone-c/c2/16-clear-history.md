# C2 task 10: Clear history keeps only completion

[C2 plan](README.md) · Decision: Q2 in [decisions](01-decisions.md) · Ratings: [Task 9](15-ratings.md)

Decided by Thomas 2026-10-27: after clearing, a student's record keeps only whether each problem
was completed; everything the student typed is removed, including (from C3) problems they
entered themselves. Today (B, C1) clearing hides sessions and help text but keeps every
submitted answer for progress and selection.

### Task 10: completion-only clear

**Files:** Modify `application/practice.py` (`clear_history`), `application/selection.py`
(read completion, not answers), `store/models.py` (only if a completion column is needed),
`templates/index.html` (confirm copy), `docs/superpowers/specs/2026-10-26-milestone-c/06-state-and-accounting.md`
(amend "B's clear_history hides sessions and retains attempts"), `docs/ops/security.md`.
Test: `tests/unit/application/test_practice.py`, `tests/unit/application/test_selection.py`,
`tests/integration/test_help_api.py`.

**Behavior:**
- Both clear buttons (Task 9) do this; the feedback button also deletes ratings.
- Kept per presented bank problem: its state (`correct` / `revealed` / `exhausted` / ...) and
  the verdict statuses needed for progress, i.e. complete or incomplete.
- Removed: every submission's typed answer (`answer_latex`, `answer_json` → a content-free
  placeholder or the rows themselves, whichever keeps the verifier/idempotency tables valid),
  help text (as today), and in C3 every own problem with its attempts and help.
- Kept, content-free: help request metadata and the usage ledger (spend and rate limits must
  not reset, spec 06), and the privacy epoch bump.
- Selection and progress must give the same next problem and the same progress numbers before
  and after a clear (they read completion, never answer text).

- [ ] **Step 1: Failing tests:** `test_clear_removes_every_typed_answer` (no submission keeps
  the student's LaTeX or MathJSON), `test_clear_keeps_completion_and_progress`,
  `test_selection_unchanged_by_clear`, `test_clear_keeps_usage_and_limits`,
  `test_replay_after_clear_shows_no_answer_text`.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Read `selection.py` first and choose: placeholder
  answers, or a completion record per problem; record the choice as a ruling. Implement.
- [ ] **Step 4:** Full suites → PASS. **Step 5:** Commit `feat(c2): clear history keeps only completion`.
