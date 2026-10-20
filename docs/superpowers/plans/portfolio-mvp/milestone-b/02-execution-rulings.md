# Milestone B: rulings made during execution

[Milestone B plan](README.md) · [Constraints and R1–R6](00-constraints.md) · [Execution status](03-execution-status.md)

Updated 2026-10-20: R24 approved in dee61a0; source review complete in 9b2e1f2.
Task 8/9 implementation outcomes and open review proposals are in [follow-ups](05-follow-ups.md).

These rulings add to the plan, and where they conflict with it, they replace it. Precedence: decisions > handoff > rulings > plan. Every ruling ends with what it costs if it is wrong.

## Setup and Codex plan review (R7–R13)

- **R7:** `.env.example` leaves `SITE_ADDRESS` empty. `smoke.sh` validates compose with `SITE_ADDRESS=localhost` exported. Cost: one line.
- **R8:** `VerifierPool(check_fn=None)` resolves `mathtutor.verify.check:check` inside the worker, so the web process never imports SymPy. Cost: a signature change.
- **R9:** Task 6 moves every fixture bundle to `schema_version` 2 with `statement_html`.
- **R10 (task 8):** the generated set gets its own gate: 0 false accepts and no `min_cases`. `min_cases` 80 applies only to the human dev set.
- **R11 (task 8):** a case labelled `unsupported` that is graded `correct` counts as a false accept.
- **R12 (task 12):** transaction B runs `UPDATE ... WHERE revision=:expected AND state='active'`.
  - If no row changes, it raises `StaleItem` (409).
  - A "database is locked" error maps to `StaleItem` or `Busy`, never a 500.
- **R13 (task 12):** a duplicate `submission_id` with no result yet:
  - under 10 s old → `SubmissionPending` (409 `submission_pending`, `Retry-After: 1`);
  - 10 s or older → regrade it (R5).

## Thomas's rulings (2026-10-15)

- **R14:** `x^{p/q}` with q odd is the real root, so it is defined for negative x. With q even it stays the principal root (base ≥ 0). Spec 03:47 has been updated.
- **R15:** `e(x+1)`-style input is still rejected, with the suggestion "Did you mean e·(x+1)?". Tasks 13 and 14 show the suggestion verbatim. Also accepted: mixed numbers rejected, `x2` rejected, `x^π` needs a positive base, and only the item's variable is allowed.
- **R16:** every FormatIssue code gets friendly copy at a Calc I/II level, with no jargon. Applies to tasks 13 and 14.

## Verifier soundness (R17–R21)

- **R17:** the Gap point is a rational point strictly inside the interval, verified exactly. If none is found, the check abstains.
- **R18:** solveset output is untrusted.
  - Abs or sign under a non-integer power → abstain.
  - Results are cross-checked at at least 64 seeded rational points.
- **R19:** violation sets are decided exactly only in two cases. Anything else → `domain_unproven`.
  - Rational functions over ℚ: exact root isolation, then a sign check on each cell.
  - Trig with a linear argument on a bounded D: lattice enumeration.
- **R20:** a `student_undefined` witness needs a positive or nonnegative violation on a whole interval neighbourhood. An isolated violation never counts.
- **R21:** a decimal answer whose expected value is irrational uses certified rounding.
  - Precision rises 60 → 120 → 240 digits.
  - If the value still straddles a rounding boundary → `unable_to_verify`.

## Function input and domain rewrites (R22–R23)

- **R22:** function input needs parentheses; a reject-only LaTeX pre-check, including `\operatorname{sin}` and `\mathrm{sin}`.
  See [decision 0003](../../../../decisions/0003-function-parentheses.md) and the [spec](../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#r22-function-input-always-uses-parentheses).
- **R23:** restrictions are rewritten and decided on their inner argument before the R19 solvers.
  Amends R18 for Abs at the top of a constraint. See the [spec](../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#r23-restrictions-are-solved-on-their-inner-argument).

## Numeric precision (R24)

- **R24:** only numeric problems explicitly requesting N places require exactly N places
  on standalone decimals; otherwise return `wrong_decimal_places`, not incorrect.
  Exact expressions remain allowed. Count original LaTeX; value mismatch with MathJSON abstains.
  No universal cap or coefficient rounding; expression decimals and removable holes are unchanged.
  Approved, not implemented: [spec](../../../specs/2026-10-20-decimal-places-design.md), [checklist](r24/README.md).
  Cost if wrong: input friction and mislabeled cases; preserve human review and FA 0.

## Rulings made inside tasks

- **Task 5:** the math libraries are pinned: `sympy==1.14.0`, `mpmath==1.3.0`.
  - A negative or bracketed decimal (`Negate`/`Delimiter` around `num`) is read as a decimal literal by both `precheck` and `check`, via one shared helper, `decimal_literal`.
- **Task 6:**
  - A misconception whose LaTeX does not parse becomes `null` in `misconceptions_mathjson`.
  - Choice-problem misconceptions are choice ids.
  - Numeric answers must be constant.
  - The Docker build-stage check is not built locally (no Docker here). CI's container job is its first run.
- **Task 7:** psutil is a dev dependency, since only the tests use it. `VERIFIER_VERSION` moved to `verify/types.py`.

## Carried into later tasks

- **Tasks 12 and 13:** `check()` raises on a kind mismatch, and the pool turns that into `internal_error` plus a respawn. The web layer must return 422 before the request reaches the pool.
- **Task 16 (`docs/verifier/supported.md`):**
  - spec 03:47 should describe the real root as sign·|a|^(1/q), not `sympy.real_root`;
  - document that a choice misconception must be a choice id.
- **Task 16:** confirm the Linux-only `RLIMIT_AS` (384 MB) with SymPy loaded on CI.
