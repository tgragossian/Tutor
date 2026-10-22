# Application debugging

[Debugging index](README.md) · [API contracts](../../../contracts/README.md)

## Accounts and CSRF

- Owners: `application/auth.py`, `web/security.py`, `web/api.py`, `web/pages.py`
  under `src/mathtutor/`.
- Registration validates username/password; rule violations are 422 `invalid_input` (A6).
- A cookie-authenticated POST needs `X-CSRF-Token` or the `csrf_token` form field.
  Missing/mismatched tokens yield 403. Login rotates the session; development allows HTTP.
- Check: `uv run pytest tests/unit/application/test_auth.py tests/integration/test_auth_routes.py -q`.
- Cookie/CSP policy belongs in [security](../security.md), not duplicated route fixes.

## Session state, retries and races

- Owners: `application/practice.py`, `application/selection.py`, `store/models.py`, `store/db.py`.
- 409 `submission_pending`: retry the same submission UUID after `Retry-After: 1`.
  Reservations at least 10 seconds old may be regraded (R5/R13, A14).
  Recovery claims `submissions.lease` and grades the stored `reserved_revision`; only the lease
  holder deletes ([B-R5/B-R2 fix](../../reviews/2026-10-22-milestone-b/06-dispositions.md)). Check `lease`/`leased_at` on a stuck row.
- 409 `stale_item`: refresh current state; inspect the submitted revision and active state.
  The conditional update and `AttemptResult.applied` distinguish a losing race.
- 503 `verifier_busy`: retry the same UUID after `Retry-After: 2`.
- Format issues and `unable_to_verify` do not consume tries. Three incorrect attempts exhaust
  an item. Selection uses unseen, then incorrect, then other seen items (A11).
- Check: `uv run pytest tests/unit/application/test_practice.py tests/unit/application/test_selection.py -q`.
- For concurrent writes: `uv run pytest tests/integration/test_submit_races.py -q`.
  Inspect WAL, `busy_timeout=5000`, `BEGIN IMMEDIATE`; keep pool work outside transactions.
- Answer timing: `seconds_on_item` = `Submission.created_at` − `served_at`, not completion
  time ([B-R3 fix](../../reviews/2026-10-22-milestone-b/06-dispositions.md)).

## API validation and logs

- Owners: `web/api.py`, `web/schemas.py`, `web/messages.py`, `web/logging.py`.
- A kind mismatch is 422 before the pool; a body over 16 KB is 413.
- Decimals pass through `jsonio.loads_exact`; do not replace with float parsing.
- Trace `X-Request-ID` to JSON logs; verdict fields are `verdict_status`, `verdict_reason`,
  `verdict_method`. Passwords, cookies and CSRF tokens must not appear in logs.
- Check: `uv run pytest tests/integration/test_api.py tests/integration/test_request_log.py -q`.
- Answer leakage/process boundary: `uv run pytest tests/integration/test_no_leaks.py tests/integration/test_process_boundary.py -q`.

## MathLive and pages

- Owners: `web/static/practice.js`, `web/templates/`, `web/pages.py`, `tools/vendor.mjs`.
- Topic selection posts a form to `/sessions`; the practice page fetches the JSON API.
- Inspect CSP errors and missing vendor assets first. SRI hashes must match committed bytes.
- MathLive needs `style-src-attr 'unsafe-inline'`; [security](../security.md) records why.
- Functions require parentheses (R22); precision checks use original LaTeX (R24).
- Answer locked after retries: `pending`/`unresolved` in `check()` keep it while the server
  may hold it; only all-`verifier_busy` frees it ([B-R1 fix](../../reviews/2026-10-22-milestone-b/06-dispositions.md)).
- Check: `uv run pytest tests/integration/test_pages.py -q`, then the
  [local browser smoke](../development.md). Its MathLive click uses an 80 ms press (A18).
- [App rulings A1–A21](../../superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md)
  explain deviations from the original task recipes.
