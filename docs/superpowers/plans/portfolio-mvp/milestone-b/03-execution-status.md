# Milestone B: execution status

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md)

Updated 2026-10-15. Branch `milestone-b` (worktree `.claude/worktrees/milestone-b`).

Each task is built by a subagent, then reviewed task by task (spec plus quality), then put through fix rounds and a re-review.

## Tasks

| Task | Commits | State |
|---|---|---|
| 1 Carry-overs, exact decimals | b03faac..813597c | complete |
| 2 Types, bounds, pre-checks | 813597c..b5c05b9 | complete |
| 3 Translator | b5c05b9..ee4f4bf | built; B-C2 review fix pending (cc0dcfc is review docs) |
| 4 Equivalence | ee4f4bf..dbeea51 | complete after 2 fix rounds |
| 5 Refute and check | dbeea51..9d06779 | built after 2 fix rounds; B-C1 review fix pending |
| 6 Content check, statement HTML | 9d06779..4ec38cb | complete after 1 fix round |
| 7 Verifier pool | 4ec38cb..c4fa3ed, then the red tests | **paused mid fix round 1** |
| 8–16 | — | not started |

At c4fa3ed: 474 tests pass, 1 is skipped (Linux only), and mypy and ruff are clean.

## Task 7: where it stopped

The review of c4fa3ed found 3 Important issues:
1. `worker_ms` includes the reap and respawn time.
2. The soft budget inside `check` equals the 3 s hard deadline. It should be `deadline - 0.5`.
3. A failed respawn is permanent. It should be retried lazily.

The fix round also covers these minors:
- `alive()` must not report False while a respawn is in progress, so `/readyz` does not flap.
- A worker that replied and then died must not be reused.
- Close the pipes if `proc.start()` fails.
- Widen the timing margins in two tests.

Seven new failing tests for these are committed as a red commit. `pool.py` is not yet changed.

## Codex code review at 2f95748

- [Findings and fix order](../../../../reviews/2026-10-15-milestone-b/01-code-review.md), with linked reproductions.
- B-C1/P1: inward-rounded absolute-value interval can falsely refute equal expressions (task 5).
- B-C2/P1: computed logarithm exponent bypasses the magnitude bound (task 3).
- B-C3/P2: failed partial pool construction does not reap earlier workers (task 7).
- Full Windows suite: 474 passed, seven known pool failures, one Linux-only skip.
- Compiler tests (14), content check (6 problems), ruff and mypy pass. Docker unverified.
- **Next:** fix B-C1/B-C2, finish the seven pool fixes plus B-C3, re-review and verify, then task 8.

## Deferred minors (not blocking; decide at the final review)

- **Task 1:** `app.py` rebuilds the lowercase header set for every header; the loader tests use string-replace tricks.
- **Task 2:**
  - `\d` in `structure.py` also accepts Unicode digits;
  - the deep-tree test cannot prove the walk is not recursive.
- **Task 3:**
  - the x^0 / 0^0 convention is undocumented;
  - `assert`s sit in untrusted-input paths;
  - the digit rule is conservative.
- **Task 4:** these cases abstain (`unable_to_verify`) when they could be decided:
  - cot(x/3);
  - π, e or ln 2 in a denominator;
  - ln(x^(1/3)) on (0,∞);
  - ln(eˣ) vs x;
  - sin x/cos x vs tan x.

  Revisit the abstention rate once task 9 gives the dev-set numbers. Also, `real_roots` and trig enumeration ignore the budget (the pool's hard deadline still bounds them).
- **Task 5:**
  - `sample_points` duplicates the content schema's interval helpers;
  - the rounding path's `doit()` has no budget;
  - a Starlette/httpx deprecation warning (pre-existing).
- **Task 6:**
  - emphasis that spans `$...$` renders literal asterisks;
  - choice translation hard-codes x;
  - `\\$` is read as an escaped dollar.
- **Task 7:**
  - the respawn runs on the timed-out caller's thread;
  - first-in, first-out order among waiters is not enforced;
  - `close()` can return while a respawn is still starting.

## Human gates still ahead

- Task 9: dev-case labels.
- Task 15: new problems.
- Task 16: deploy to the host and measure memory.

Record hours in `docs/ops/hours.md`. Stop at 30 h.
