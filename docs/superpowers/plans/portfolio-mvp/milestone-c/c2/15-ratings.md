# C2 task 9: rate a help response (1–5, optional comment)

[C2 plan](README.md) · Previous: [UI](12-ui.md) · Decision: Q9 in [decisions](01-decisions.md)

Requested by Thomas 2026-10-27: under every shown help response (hint, feedback, explain,
question), five buttons 1–5 and an optional, skippable written comment.

### Task 9: ratings

**Files:** Create `migrations/versions/0007_help_ratings.py`, `src/mathtutor/help/ratings.py`,
`src/mathtutor/help/ratings_report.py`. Modify `store/models.py`, `web/api.py`, `web/schemas.py`,
`application/practice.py` (`clear_history`), `help/messages.py`, `templates/practice.html`,
`static/practice.js`, `static/app.css`. Test: `tests/unit/help/test_ratings.py`,
`tests/integration/test_help_ratings_api.py`, `tools/web/help_panel.test.mjs`.

**Interfaces — produces:**
- `HelpRating(Base)`, table `help_ratings`: `id`, `request_id` (unique, FK
  `help_requests.request_id`), `user_id` (FK users), `rating: int` (1–5), `comment: str | None`
  (Text, ≤ 1,000 characters after `normalize_question`-style normalization), `created_at`,
  `updated_at`. Migration `0007`, `down_revision` = C2's `0006`.
- `RatingService.rate(user_id, request_id, rating, comment) -> None`: owner only (`Forbidden`
  otherwise; unknown id `NotFound`); only finished rows with shown text or a fixed message
  (`delivered`, `fallback`, `abstained`), else `InvalidAction(code="not_rateable")`; upsert
  (a later call replaces rating and comment; `comment=None` keeps the existing comment, `""`
  removes it). Never touches tries, verdicts, the ladder or the ledger.
- `POST /api/help/{request_id}/rating` body `{"rating": 1-5, "comment": str | null}` →
  204; CSRF and the per-user help limiter apply; 422 outside 1–5.
- `clear_history`: in the same transaction, `comment = NULL` on the user's ratings; the
  numbers stay (content-free, like usage).
- `python -m mathtutor.help.ratings_report --db <url>`: count and mean rating by help type,
  hint level, mistake type and serving model; never prints comments.

UI (copy is Q9): after `showHelp`, a row "Was this helpful?" with buttons `1`…`5`
(`aria-pressed`, `aria-label="Rate 3 of 5"`), then a "Tell us more (optional)" link that opens
a textarea (`maxlength="1000"`) and "Send". One click sends the number at once; the comment is
a second request. "Thanks!" replaces the row's prompt; a new help response resets it. Ratings
use the C1-R8 retry rule: an unanswered rating keeps its body for one retry.

- [ ] **Step 1: Failing tests:** `test_rate_then_rerate_replaces`, `test_rate_someone_elses_request_forbidden`,
  `test_pending_or_stale_not_rateable`, `test_comment_never_logged_or_sent` (sentinel text in
  no log record, request-log line or generator request), `test_clear_history_keeps_number_drops_comment`,
  `test_rating_does_not_change_ladder_or_tries`, `test_report_prints_no_comment`; API: 204,
  422 for 0 and 6, CSRF required; Node: `rating buttons appear after help`, `one click sends
  the number`, `comment is optional and separate`, `new help resets the rating row`.
- [ ] **Step 2:** Run them → FAIL. **Step 3:** Implement. **Step 4:** full suites → PASS.
- [ ] **Step 5:** Commit `feat(c2): rate help responses 1-5 with an optional comment`.
