# Dispositions (Claude, 2026-10-21)

[Review index](README.md) · [Validation](03-validation.md)

All five findings were confirmed and fixed in **4eba48f** (`fix: address milestone B review B-A1..B-A5`).
Regression tests: [tests/integration/test_review_findings.py](../../../tests/integration/test_review_findings.py),
each written first and observed failing (10 of 12 failed before the fix; the two that passed
cover behaviour that was already correct).

| ID | Fix | Regression |
|---|---|---|
| B-A1 | `ActionRequest` carries `session_item_id`; `_act` rejects any other presentation with 409 `stale_item`. The page sends it and runs one mutation at a time. | duplicate Skip; delayed Advance/Reveal/Skip after the next item appears; 4 concurrent Skips → 1 wins |
| B-A2 | `loads_exact(..., max_depth=40)` scans depth iteratively before parsing (strings ignored); `RecursionError` also maps to `JsonTooDeep` → 422 `invalid_request`. | 3000 nested arrays and 2000 nested objects under 16 KB → 422, pool untouched; `[` inside strings still accepted |
| B-A3 | Only `write_transaction()` starts `BEGIN IMMEDIATE`; reads are deferred (no lock under WAL). Login reads and verifies outside the write lock. An app-wide handler maps lock errors to 503 `database_busy` + `Retry-After: 2`; error pages tolerate DB failure. | with a writer holding the lock: `/api/auth/me`, current, history and `/` answer 200 in under 3 s; Skip, API login and form login give 503; recovery after release |
| B-A4 | Policy: **immutable snapshots**. `session_items.problem_json` stores the compiled problem at presentation time; views, grading, replay and reveal use it. New presentations use current content. | edited and removed problem: old presentation keeps statement, grading spec and revealed answer; a new user's presentation gets the edit and new version |
| B-A5 | The format-issue branch checks the presentation is still current, active and at the expected revision, else `StaleItem`. The page ignores replies about a problem no longer shown. | Skip during grading + format issue → `StaleItem`; browser smoke: Skip disabled while a slow Check is in flight, double-click Skip sends one request |

## Notes

- `problem_json` and `attempt_results.applied` were added to the 0001 baseline, which has never
  been deployed. Local databases from before 4eba48f must be recreated.
- Codex's [repro_app.py](repro_app.py): B-A2/B-A3/B-A4 probes now pass. B-A1/B-A5 probes fail only
  because they use the old action signature (no `session_item_id`), which the fix removes; the
  regression tests above cover their intent.
- Checks after the fix: 851 Python tests (1 skipped), 19 Node tests, ruff, mypy, content check,
  docs check, and the browser smoke against a local server, all passing. No Docker, Linux CI or
  production run.
