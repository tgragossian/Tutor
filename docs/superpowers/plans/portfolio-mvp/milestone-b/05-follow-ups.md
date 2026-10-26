# Milestone B: follow-ups and deferred observations

[Execution status](03-execution-status.md) · [Plan](README.md) · [Rulings](02-execution-rulings.md)

Updated 2026-10-22. Current review findings come first; historical/deferred observations follow.

## Whole-branch review findings (resolved)

[Fix recheck](../../../../reviews/2026-10-22-milestone-b/07-recheck.md): B-R1/B-R2/B-R3/B-R5
verified fixed in ca54407. B-R4's recheck case (HTTP 200 `unable_to_verify/internal_error`
counted as graded) fixed in 04de2d2. Thomas reports all fixes deployed at 8057590 with migration 0003.
Deferred defense in depth: SQLite AUTOINCREMENT on `submissions` (needs a table rebuild with
foreign keys on); the transaction-B identity check already makes a reused row id harmless.

Prior [B-A1–B-A5](../../../../reviews/2026-10-21-milestone-b/04-dispositions.md) were fixed in
4eba48f; their normal regressions pass in the fresh 904-test suite. They are not open work.

## Resolved for task 9

- Done: [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md) B-E1/B-E2
  in bdb1710 (approved reviewer, label/category coverage, empty sets fail, `--draft`).
- Done: `d-log2-01` in 832740f. After the B-C2 bound, a computed exponent is proven equal to
  the nearest small rational in its enclosure; enclosed-but-unproven abstains.
- Done: `d-181-05` resolved by Thomas (R22 option A, parentheses required); the case is
  `(1-\sin(x))^2-\cos(x)(x+\cos(x))`, label `correct`. See [decision 0003](../../../../decisions/0003-function-parentheses.md).
- Done: [R22/R23 plan](r22-r23/README.md) (ea6748b..19db4ab). Historical pre-R24 draft: FA 0/54, FR 0/52,
  coverage 52/52, agreement 136/136 on 136 cases. All nine review-sheet disagreements now
  agree; #8 `d-explog-03` (ln(e^x) = x on R, label confirmed by Thomas) was resolved by 19db4ab
  (typed e^x is Power(e, x) and counts as always positive). Inline-spec LaTeX follows R22 too.
  The 25 rewritten inputs (not the scan's 26) exclude `d-lnsq-02`, whose `\lvert` bars R22 accepts.
- Found and closed: the R22 pre-check missed `\operatorname{sin}x` and `\mathrm{sin}x`
  (Compute Engine parses both as `Sin`; MathLive produces the operatorname form from typing).
  Closed in 098b7ba with tests; regression case `d-r22-05`.
- Human review completed in 9b2e1f2: all 136 source rows are `tg`, including seven R24 labels.
  R24 landed in a76985d; b5ad4b2 recaptures source exactly. e995438 records passing non-draft
  [dev-b.json](../../../../../evals/verifier/results/dev-b.json); 8a0bb40 enables the dev CI gate.
- d673400 fixes Linux pool-test teardown (competing worker reap). CI run 39504828416 is green;
  Thomas reports 722 Linux tests passed, including memory containment. Task 9 is complete.
- `dev-draft.json` reports `0.1.0+dev`; published runs should record the actual code SHA
  through `MATHTUTOR_GIT_SHA`. Keep the existing draft result unchanged.

## Deferred observations from tasks 1–7

- Task 1: repeated lowercase header-set construction; string-replace loader test setup.
- Task 2: `\d` accepts Unicode digits; deep-tree test alone does not establish iterative traversal.
- Task 3: document x⁰ / 0⁰ convention; assertions in input paths; conservative digit rule.
- Task 4: R23 resolved the listed cot(x/3), ln(eˣ) and sin x/cos x dev abstentions.
  Other observations (π/e/ln 2 denominators and ln(x^(1/3))) need case-specific review.
  `real_roots` and trig enumeration lack soft budget checks; the pool enforces the hard deadline.
- Task 5: duplicated interval helpers in `sample_points`; rounding `doit()` has no soft
  budget; existing Starlette/httpx deprecation warning.
- Task 6: emphasis spanning `$...$` renders literal asterisks; choice translation fixes
  the variable to x; escaped backslash-dollar handling needs review.
- Task 7: `alive()` may synchronously respawn; no backoff on persistent startup failure;
  `BaseException` during spawn can leak the counter; respawn runs on the caller's thread;
  waiting callers have no FIFO guarantee.
- B-C fixes: deeply nested constant-base digit estimates may undercount (cost only);
  consider extracting the interval walker to remove the lazy translator/refute cycle.

## Task 8/9 notes and later dependencies

- 4138181 adds no-crash gates to both sets and full agreement to the generated gate;
  generated evaluation has no 80-case minimum. The CLI uses the worker pool.
- a115846 adds `raw_latex` / `raw_keys` and accepts empty/incomplete format issues as
  agreement for `unsupported` labels. No additional deferred minors were recorded
  in these commit bodies; gate observations above come from Codex's review.
- Deep nested-root capture can crash Chromium; the harness retries a fresh page.
  Keep this browser limitation visible when task 14 handles adversarial input.
- Tasks 12–14 implement atomic writes/replay, friendly messages and pre-pool kind checks;
  see [A1–A18](06-app-track-rulings.md) and [app debugging](../../../../ops/debugging/01-app.md).
- Task 15: all 16 drafts approved by Thomas; 22 reviewed problems deployed ([review](../../../../../content/review/README.md)).
- **Verifier speed (2026-10-21):** wrong answers to nested trig compositions such as
  `sin(cos 7x)` time out (3 s) and return `unable_to_verify` instead of `incorrect`; the
  correct answer proves in 0.03 s. Exercise 235 was dropped for this. Safe (never a false
  accept) but poor feedback; look at refutation cost for nested compositions.
- **content_check has no hard deadline:** in-process `check()` overruns its soft budget, so a
  slow problem hangs the CLI (and CI/Docker build) instead of reporting it. Run each problem
  through the pool, or a subprocess with a timeout, and report `timeout` as a defect.
- Task 16: storage/migrations, image e2e, verifier docs and deployment implemented.
  [Host sizing](../../../../ops/host-sizing.md) is deferred to C by Thomas; B-R4 fixed.
  [Release debugging](../../../../ops/debugging/02-release.md) records current paths.
