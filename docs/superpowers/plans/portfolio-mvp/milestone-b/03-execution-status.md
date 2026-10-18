# Milestone B: execution status

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md)

Updated 2026-10-18. Branch `milestone-b` (worktree `.claude/worktrees/milestone-b`).

Each task is built by a subagent, then reviewed task by task (spec plus quality), then put through fix rounds and a re-review.

## Tasks

| Task | Commits | State |
|---|---|---|
| 1 Carry-overs, exact decimals | b03faac..813597c | complete |
| 2 Types, bounds, pre-checks | 813597c..b5c05b9 | complete |
| 3 Translator | b5c05b9..ee4f4bf, b7f23ad | complete; B-C2 fixed in b7f23ad |
| 4 Equivalence | ee4f4bf..dbeea51 | complete after 2 fix rounds |
| 5 Refute and check | dbeea51..9d06779, 8346d2a | complete; B-C1 fixed in 8346d2a |
| 6 Content check, statement HTML | 9d06779..4ec38cb | complete after 1 fix round |
| 7 Verifier pool | 4ec38cb..10611a5 | complete after fix round 1; B-C3 fixed in 10611a5 |
| 8–16 | — | not started |

At 10611a5: 531 tests pass, 1 is skipped (Linux only), and mypy and ruff are clean.

## Codex code review at 2f95748

- [Findings and fix order](../../../../reviews/2026-10-15-milestone-b/01-code-review.md), with linked reproductions.
- B-C1/P1: inward-rounded absolute-value interval can falsely refute equal expressions (task 5).
- B-C2/P1: computed logarithm exponent bypasses the magnitude bound (task 3).
- B-C3/P2: failed partial pool construction does not reap earlier workers (task 7).
- Full Windows suite: 474 passed, seven known pool failures, one Linux-only skip.
- Compiler tests (14), content check (6 problems), ruff and mypy pass. Docker unverified.
- **Fixed 2026-10-18** (each reviewed clean): B-C1 8346d2a, B-C2 b7f23ad, pool + B-C3 10611a5.
- **Next:** task 8 under R10–R13.

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
  - `alive()` retries a respawn synchronously, so `/readyz` can wait one worker start;
  - no respawn backoff under persistent start failure; a `BaseException` in spawn leaks the counter;
  - the respawn runs on the timed-out caller's thread;
  - first-in, first-out order among waiters is not enforced;

- **B-C fixes:**
  - x^(log_2 8) vs x^3 is graded incorrect (R15 positive base); reduce exact-rational
    constant exponents first — revisit with task 9 false-reject numbers;
  - constant-base digit estimate can undercount with deep nesting (cost only);
  - lazy `refute` import in `translate`; extract the interval walker to its own module.

## Human gates still ahead

- Task 9: dev-case labels.
- Task 15: new problems.
- Task 16: deploy to the host and measure memory.

Record hours in `docs/ops/hours.md`. Stop at 30 h.
