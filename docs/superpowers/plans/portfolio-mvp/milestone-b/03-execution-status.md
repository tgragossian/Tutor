# Milestone B: execution status (main snapshot)

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md) · [Follow-ups](05-follow-ups.md)

Updated 2026-10-22. Tasks 1–14 merged and **deployed** (live from `main` 78bbcd6);
task 15 complete (Thomas reviewed all 22 problems 2026-10-22, not yet deployed); task 16 partly done.

Current project status (2026-10-22): tasks 10–15 are complete on `milestone-b`; task 16
is partial. The table below records main only. Follow the
[handoff](../../../../../handoff.md) to the branch status; do not restart task 10.

## Tasks

| Task | Commits | State |
|---|---|---|
| 1 Carry-overs, exact decimals | b03faac..813597c | complete |
| 2 Types, bounds, pre-checks | 813597c..b5c05b9 | complete |
| 3 Translator | b5c05b9..ee4f4bf, b7f23ad | complete; B-C2 fixed |
| 4 Equivalence | ee4f4bf..dbeea51 | complete after two fix rounds |
| 5 Refute and check | dbeea51..9d06779, 8346d2a | complete; B-C1 fixed |
| 6 Content check, statement HTML | 9d06779..4ec38cb | complete after one fix round |
| 7 Verifier pool | 4ec38cb..10611a5, d673400 | complete; Linux test cleanup fixed |
| 8 Evaluation runner and generated gate | 55744b8, 4138181, bdb1710 | complete; reviewer/category checks included |
| R22/R23 | ea6748b..19db4ab, fe6bd4a | complete; [plan](r22-r23/README.md) |
| R24 | a76985d | implemented with tests first; [checklist](r24/README.md) |
| 9 Human dev cases | 9b2e1f2..8a0bb40 | complete: review, recapture, release result and CI |
| 10 Store | d865179 | complete; amended in 11–12 ([rulings](06-app-track-rulings.md)) |
| 11 Auth | 73ae3af | complete |
| 12 Practice service | 458f2ca | complete; races run 3× clean |
| 13 JSON API | abda25e | complete |
| 14 Pages, MathLive | c52305d | complete; manual browser check passed |
| 15 Content, smoke | 5fd8952, ba2575b | complete: 22 problems `human_verified` by Thomas 2026-10-22 ([review](../../../../../content/review/README.md)) |
| 16 Release | e6da0e5, 375ab7c | done; burst measured on the host, 1 GB kept as a recorded exception (revisit in milestone C) |

## Evidence and debugging

- [Verification evidence](07-verification-evidence.md): reviewed verifier results, historical
  CI runs and the app-track checks reported in the 2026-10-21 handoff.
- [Debugging tree](../../../../ops/debugging/README.md): local setup, symptoms, files and tests.
- [App rulings A1–A21](06-app-track-rulings.md) amend task recipes for persistence and UI.

## Review dispositions

- [2026-10-15 review](../../../../reviews/2026-10-15-milestone-b/01-code-review.md):
  B-C1 8346d2a, B-C2 b7f23ad, B-C3 and pool fixes 10611a5.
- [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md):
  B-E1/B-E2 fixed in bdb1710; `d-log2-01` fixed in 832740f; R22/R23 resolved other disagreements.
- 86cac1d restricts choices to listed IDs; 634c968 suggests both readings of `sin^-1(x)`.
- Thomas reviewed all 136 source rows in 9b2e1f2. R24 and recapture now agree with every label.

## Review follow-up (2026-10-21)

[Code review](../../../../reviews/2026-10-21-milestone-b/README.md) B-A1–B-A5: all fixed in 4eba48f
with regression tests ([dispositions](../../../../reviews/2026-10-21-milestone-b/04-dispositions.md)).

## Remaining actions

See the [handoff](../../../../../handoff.md) "Resume here": one fresh whole-branch review (Codex)
before milestone B exit. Host sizing is deferred to milestone C as a recorded exception.

Record actual hours in the [hours log](../../../../ops/hours.md); no B actuals are supplied.
At 30 h, stop at the next task boundary for a scope/date/contingency decision with Thomas.

## Documentation sync (2026-10-21)

Synced handoff, indexes, task recipes and operations against d428bd7 and the local code.
Added evidence and debugging children; preserved original references and dated reviews.
The initial sync changed Markdown only. The later [code review](../../../../reviews/2026-10-21-milestone-b/03-validation.md)
reran local checks and added isolated probes; no production code was changed.
