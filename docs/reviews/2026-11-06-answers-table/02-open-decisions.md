# Answers table: release decisions

[Brief](README.md)

These were raised in review. Release fixes adopt the recommendations for 1–3 and 5;
Thomas checks the rendered copy and student flow after deployment.

1. **Clear history keeps the one-hint lock.** Clearing erases hint text but the "already had
   a hint" check still counts the cleared hint, so a student on the same open problem sees
   "You've already had a hint…" with no way to see it again. Recommend: count only hints not
   cleared (`cleared_at IS NULL`) for the lock.
   **Adopted**, with regression coverage for a cleared wrong-answer hint.
2. **Wording after the last try.** On an exhausted item (5 wrong answers) a repeat Hint says
   "Try again with it in mind", but no tries remain; after only an `unable_to_verify` answer
   the student sees the no-attempt text; after a hinted wrong answer and then an
   `unable_to_verify` one, a repeat Hint says "…for this answer". Recommend: a third text for
   exhausted items ("You've used all your tries. Use Show answer or Explain this.") and pick
   the text from the latest graded attempt, not only the latest wrong one.
   **Adopted**; an unverifiable latest answer gets its own wording.
3. **The try-again message replaces the hint on screen.** The student loses sight of the hint
   the message refers to. Recommend: show the message below the existing hint instead.
   **Adopted** when the hint remains visible on the page.
4. **Privacy copy.** Plan copy D11 replaced the earlier "wording pending Thomas's approval"
   note in `docs/ops/security.md`. The practice page says a wrong answer goes to Anthropic
   when help is enabled, including without a help click. Thomas checks it on the live site.
5. **Per-user classifier cap.** Classify calls skip the per-user help limits by design (D5),
   so one scripted account could drain the shared $10 month budget (it fails safe: help
   stops, no overspend). Recommend: a separate daily classify cap per user, e.g. 100.
   **Adopted**: 100 classifier admissions per user per trailing day, separate from help limits.
6. **Deploy timing.** After Codex review and fixes: fresh DB backup, then the runbook order.
   **Authorized for today by Thomas.** Rehearsal on a live backup copy and container smoke
   remain release gates; Thomas tests the live browser afterward.
