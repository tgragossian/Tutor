# Codex recheck of ca54407 — 2026-10-22

[Review](README.md) · [Author dispositions](06-dispositions.md) · [Handoff](../../../handoff.md)

Reviewed identical `main` / `milestone-b` **f3a4e40**, including fix ca54407.
**B-R1/B-R2/B-R3/B-R5 are verified fixed in the reviewed paths. B-R4 remains partially open.**
No production code was changed by this recheck. Documentation and isolated probes are in main.

Later status: 04de2d2 fixes B-R4; [dispositions](06-dispositions.md) records passing probes.
Thomas reports deployment at 8057590 with migration 0003. Findings below retain the f3a4e40 snapshot.

## Remaining B-R4 (P2): a crashed verifier still passes the load run

Owner: [submit_burst.py](../../../tools/load/submit_burst.py), lines 78–84, 181–185, 219–224.

The real verifier reports crashes as HTTP **200** with
`outcome = {status: "unable_to_verify", reason: "internal_error", method: "none"}`.
`burst()` discards the reason and retains only `unable_to_verify`; `_expected()` and
`graded()` accept that status. A run in which every verifier call fails therefore exits 0
and is counted as having performed graded work. `measure.sh` now propagates exit codes
correctly, but cannot detect a false success from the CLI.

The new [probe](repro_recheck.py) stubs only HTTP/setup, then exercises the real threaded
burst, outcome extraction, summary and CLI. Two 200/internal_error replies produce
`200 unable_to_verify: 2` and **exit 0**, where the assertion requires exit 1.
The existing test covers HTTP 500/internal_error, which is not the verifier crash contract.

Fix: retain the verdict reason through aggregation and reject `internal_error` regardless
of HTTP status. Distinguish ordinary timeout/domain abstention from a crashed verifier;
do not simply reject all `unable_to_verify` outcomes. Add a full-path regression for the
real 200/internal_error shape, including a mixture with successful grades and all-crash runs.
Keep the recorded host measurement (8 incorrect grades / 8 verifier_busy); it is unaffected.
This is a load-tool defect, not a new blocker to deploying the application integrity fixes.

## Accepted recovery departures

- **Any legitimate holder may finalize:** acceptable for this immutable answer/snapshot and
  stored revision. UUID/presentation checks prevent cross-answer writes; the unique result
  constraint and transactional rollback prevent a second state transition. A new probe lets
  recovery finish first, then the original holder finishes: it replays the existing result,
  leaving one result and one revision increment. The original B-R5 probe also passes.
- **No AUTOINCREMENT rebuild:** acceptable. A new probe actually deletes a reservation,
  reserves Bob's answer with the same integer ID, then tries to finalize Alice's old answer.
  It returns `StaleItem`, stores no result and changes neither presentation. The identity
  check makes this optional safeguard unnecessary for closing B-R5.

## Migration and other fixes

- [Populated upgrade probe](repro_upgrade.py): migrate 0002 with a completed result and a
  pending submission to 0003. All old fields/results preserved, foreign-key check clean,
  new fields `(NULL, 0, NULL)`, schema version 0003 and submission table root page unchanged.
- Original state/timing probes pass. Legacy pending rows are rejected without guessing a
  revision; completed rows remain replayable. B-R3 uses the original persisted timestamp.
- All seven controller tests and the original B-R1 Node probe pass. Inspected the real-browser
  regression added to the smoke script; browser execution was not repeated in this recheck.
- Database-error/format rejection and shell exit propagation are implemented for B-R4;
  the remaining issue is specifically verifier internal-error outcomes.

## Fresh validation

- Python suite: **904 passed, 3 skipped**, 153.20 s; one existing Starlette/httpx warning.
  Skips: Linux memory containment and two POSIX shell cases. An initial sandboxed run failed
  on temporary-directory access; the approved rerun produced these results.
- Node suite: **26 passed**; original UI probe: **1 passed**.
- Original four Python probes plus three recheck probes: **6 passed, 1 failed** (B-R4).
  Populated migration probe: **1 passed**. All probes are outside normal collection.
- Repository lint/format, source mypy and docs checks pass after recheck edits.
- No fresh browser, Docker, Linux CI, production or verifier evaluation CLI run here;
  the verifier implementation is unchanged. Prior browser/CI claims remain author-reported
  in [dispositions](06-dispositions.md), not independently fetched by this pass.

Run: `uv run pytest docs/reviews/2026-10-22-milestone-b/repro_recheck.py docs/reviews/2026-10-22-milestone-b/repro_upgrade.py -q -p no:cacheprovider`.
Next: fix the remaining B-R4 case before B closure; deploy migration 0003 and record actual hours.
