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
  **Open [B-R5/B-R2](../../reviews/2026-10-22-milestone-b/01-recovery.md):** age does not prove
  the original caller died; cleanup can delete live work, and recovery loses its original revision.
- 409 `stale_item`: refresh current state; inspect the submitted revision and active state.
  The conditional update and `AttemptResult.applied` distinguish a losing race.
- 503 `verifier_busy`: retry the same UUID after `Retry-After: 2`.
- Format issues and `unable_to_verify` do not consume tries. Three incorrect attempts exhaust
  an item. Selection uses unseen, then incorrect, then other seen items (A11).
- Check: `uv run pytest tests/unit/application/test_practice.py tests/unit/application/test_selection.py -q`.
- For concurrent writes: `uv run pytest tests/integration/test_submit_races.py -q`.
  Inspect WAL, `busy_timeout=5000`, `BEGIN IMMEDIATE`; keep pool work outside transactions.
- Wrong answer timing: [B-R3](../../reviews/2026-10-22-milestone-b/02-ui-and-timing.md#b-r3-p2-stop-student-timing-at-submission)
  traces `seconds_on_item` to completion time instead of the persisted submission time.

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
- Edited answer graded as the previous input after retries: inspect retained `pending` in
  `check()`; [B-R1 reproduction](../../reviews/2026-10-22-milestone-b/02-ui-and-timing.md#b-r1-p2-retry-the-answer-the-student-can-see).
- Check: `uv run pytest tests/integration/test_pages.py -q`, then the
  [local browser smoke](../development.md). Its MathLive click uses an 80 ms press (A18).
- [App rulings A1–A21](../../superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md)
  explain deviations from the original task recipes.
