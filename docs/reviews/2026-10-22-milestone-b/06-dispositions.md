# Dispositions (Claude, 2026-10-22)

[Review](README.md) · [Recovery](01-recovery.md) · [UI and timing](02-ui-and-timing.md) · [Release](03-release.md)

All five findings were confirmed by the probes and fixed in **ca54407**
(`fix: review B-R1-B-R5 …`). The probes beside this review now pass unchanged; their cases
moved into normal tests. Production must apply migration **0003** on the next deploy.

## B-R5 (P1) and B-R2: recovery lease and original revision

- Migration 0003 adds `submissions.reserved_revision`, `lease` (default 0) and `leased_at`.
  Added columns only, so no table rebuild and foreign keys stay intact.
- `_reserve` stores the revision; the original request holds lease 0.
- An orphan (no result, `leased_at`/`created_at` ≥ 10 s old) is recovered only through
  `_claim`: one conditional `UPDATE … SET lease = lease + 1` on id, UUID, the lease seen and
  "no result yet". A second recovery sees a fresh `leased_at` and gets `submission_pending`.
- Recovery grades against the **stored** `reserved_revision`, never the retry's body. Ruling
  A14 is amended accordingly. Pre-0003 orphans (NULL revision) are deleted by the claimant and
  answered `stale_item` (the student resubmits), never guessed.
- `_release` deletes only where id, UUID and the caller's lease still match and no result
  exists. On `verifier_busy` only the original request (lease 0) releases; a busy recovery
  leaves the row for a later retry. Format results release under the caller's lease.
- Transaction B first re-reads the submission and requires the same UUID and presentation, so
  a reused row id can never receive another answer's result.
- **Deviation:** any request holding the reservation may finalize, not only the newest lease
  holder: both grade the same stored answer against the same stored revision, and the unique
  `attempt_results.submission_pk` keeps exactly one result (the loser replays it).
- **Not done:** SQLite AUTOINCREMENT. It needs a table rebuild with foreign keys enforced on a
  live database; with the identity check above, a reused id is harmless. Recorded in follow-ups.

Tests: `tests/unit/application/test_recovery.py` (live reservation survives a busy duplicate and
another user's reservation; exclusive lease; busy recovery keeps the row; format cleanup; the
original owner cannot delete after a recovery claimed; original-revision recovery still works;
newer-revision retry is stale; pre-0003 rows dropped).

## B-R3: answer time ends at submission

`seconds_on_item` = original `Submission.created_at` − `served_at`, carried in the reservation
and kept across recovery. Historical rows are not rewritten. Tests: grading delay of 7 s keeps
42 s; an orphan recovered 5 minutes later keeps its 30 s.

## B-R1: the page sends the answer the student sees

`practice.js` locks the answer (MathLive read-only, radios disabled) while a check is in
flight. If any retry was ambiguous (lost reply, `submission_pending`, any 503 other than
`verifier_busy`), the answer stays locked after the retries, the page says it is still being
checked, and Check resends the same UUID and body. Only when every reply was `verifier_busy`
(the server kept nothing) is the payload dropped, so an edit becomes a new answer with a new
UUID. Tests: `tools/web/practice_controller.test.mjs` (7 cases, including choices and a lost
successful reply) and a Playwright step in `tools/e2e/smoke.mjs` with real MathLive.

## B-R4: load checks fail on failures

`submit_burst.py` accepts only 200 with a verdict or 503 `verifier_busy`; `database_busy`,
format replies, other errors and transport failures are unexpected, and zero graded answers
fails the run. `measure.sh` keeps the burst's exit status, still prints memory, and exits
non-zero with a warning. Tests: `tests/unit/test_submit_burst.py`, `tests/unit/test_measure_sh.py`
(Linux CI). The recorded 2026-10-22 host run (8 graded, 8 `verifier_busy`) stays valid.

## Verification

Windows: 904 Python passed, 3 Linux-only skips; 26 Node; lint, format, mypy; content check
(22); dev and generated gates pass; all five review probes pass; browser e2e passed against a
local production-mode server migrated to 0003. Linux CI on ca54407: see the handoff.
