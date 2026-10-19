# Milestone B: follow-ups and deferred observations

[Execution status](03-execution-status.md) · [Plan](README.md) · [Rulings](02-execution-rulings.md)

Updated 2026-10-19. Observations are not new rulings or completed fixes.
Keep release-relevant evaluation issues ahead of optional cleanup.

## Resolve before task 9 is called complete

- Done: [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md) B-E1/B-E2
  in bdb1710 (approved reviewer, label/category coverage, empty sets fail, `--draft`).
- Done: `d-log2-01` in 832740f. After the B-C2 bound, a computed exponent is proven equal to
  the nearest small rational in its enclosure; enclosed-but-unproven abstains.
- Done: `d-181-05` resolved by Thomas (R22 option A, parentheses required); the case is
  `(1-\sin(x))^2-\cos(x)(x+\cos(x))`, label `correct`. See [decision 0003](../../../../decisions/0003-function-parentheses.md).
- Done: [R22/R23 plan](r22-r23/README.md) (ea6748b..19db4ab). Fresh draft: FA 0/54, FR 0/52,
  coverage 52/52, agreement 136/136 on 136 cases. All nine review-sheet disagreements now
  agree; #8 `d-explog-03` (ln(e^x) = x on R, label confirmed by Thomas) was resolved by 19db4ab
  (typed e^x is Power(e, x) and counts as always positive). Inline-spec LaTeX follows R22 too.
  The 25 rewritten inputs (not the scan's 26) exclude `d-lnsq-02`, whose `\lvert` bars R22 accepts.
- Found and closed: the R22 pre-check missed `\operatorname{sin}x` and `\mathrm{sin}x`
  (Compute Engine parses both as `Sin`; MathLive produces the operatorname form from typing).
  Closed in 098b7ba with tests; regression case `d-r22-05`.
- Reviewer placeholder is `pending`, replacing the plan's empty string. Nonblank validation
  does not establish human review. Regenerate captures after Thomas records review in YAML.
- `dev-draft.json` reports `0.1.0+dev`; published runs should record the actual code SHA
  through `MATHTUTOR_GIT_SHA`. Keep the existing draft result unchanged.

## Deferred observations from tasks 1–7

- Task 1: repeated lowercase header-set construction; string-replace loader test setup.
- Task 2: `\d` accepts Unicode digits; deep-tree test alone does not establish iterative traversal.
- Task 3: document x⁰ / 0⁰ convention; assertions in input paths; conservative digit rule.
- Task 4: conservative abstentions for cot(x/3), π/e/ln 2 denominators, ln(x^(1/3)) on
  positive reals, ln(eˣ), and sin x/cos x. `real_roots` and trig enumeration lack soft
  budget checks; the pool still enforces the hard deadline.
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
- Tasks 12–14 must honor R12/R13 atomic writes and replay responses, R15/R16 friendly
  messages, and kind-mismatch rejection before the pool. Task 16 owns Linux sizing,
  supported-expression documentation and deployment evidence.
