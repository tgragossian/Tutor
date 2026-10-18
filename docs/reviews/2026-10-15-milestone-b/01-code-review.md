# Milestone B code review — 2026-10-15

[Review index](README.md) · [Reproductions](02-reproductions.md) · [Handoff](../../../handoff.md)

Reviewed `main` bb15c91 through `milestone-b` 2f95748; tasks 1–6 and partial task 7.
Focus: translation, proof/refutation, pool lifecycle, content compilation and B carry-overs.
Tasks 8–16 are not implemented; their absence is not a defect in this review.
No implementation changes made. The findings below remain open for Claude.

## B-C1 — P1: absolute-value enclosure can exclude the true value

Location: [refute.py](../../../src/mathtutor/verify/refute.py), lines 108–114 (`_abs`).
When a box crosses zero, `max(-lo, hi)` negates an ordinary `mpmath.mpf`.
Only `iv.dps` is raised to 60; ordinary `mp` arithmetic still uses its default precision.
The negation can round inward before the endpoint is put back into an interval.

Reproduction C1 uses two accepted, exactly equal constant expressions.
`enclose(student)` returns an upper bound about 5.086e-6 below the exact value;
`refute(student, expected)` then returns `counterexample`.
This breaks the certified-refutation contract. For this simple pair, the full dispatcher
proves equality first; an end-to-end false rejection by `check` was not demonstrated.

Fix endpoint arithmetic with interval operations or exact/directed endpoint operations.
Do not rely on merely increasing ordinary precision. Add enclosure-containment and
equal-expression refutation regressions, including cancellation and zero-crossing boxes.

## B-C2 — P1: computed logarithms bypass the exponent bound

Locations: [translate.py](../../../src/mathtutor/verify/translate.py), lines 314–318 and
409–425 (`_raise`, `_log_base`; also audit digit propagation through reciprocal functions).
`const_digits` does not bound a logarithm when its base is arbitrarily close to 1.
`Log(e, Exp(1/N))` is assigned 3 digits although its exact value is N.
Consequently `Power(2, Log(e, Exp(1/N)))` translates even for N = 10^29.
Its exponent simplifies exactly to 10^29, exceeding the 1,000 exponent limit.

The proof stage may attempt to materialize an enormous integer before a soft budget check.
The worker hard limit remains a fallback, but this bypass defeats the planned early rejection
and can repeatedly consume/kill workers (Windows has no address-space cap).
Reproduction C2 evaluates only the exponent; never evaluate the outer power at N = 10^29.

Use conservative bounds that account for small denominators/logarithms, or reject a constant
exponent whose magnitude cannot be bounded safely before evaluation. Add regressions for
both `Log` and equivalent `Divide`/`Ln` forms; retain rejection as `input_too_large`.

## B-C3 — P2: partially constructed pools leak earlier workers

Location: [pool.py](../../../src/mathtutor/verify/pool.py), lines 172–181 (`__init__`).
The worker-creation list comprehension executes outside the cleanup `try`.
For size >= 2, if a later `_new_worker()` raises, already-started workers are never stopped
and no completed pool is returned for the caller to close. The default size 1 avoids this
specific path; size 2 is already supported and tested.
Reproduction C3 injects a failure on the second creation and observes zero cleanup calls.

Create workers incrementally inside the cleanup scope and reap every worker created before
failure. Add a partial-startup regression. This is separate from the existing red test for
closing the two pipe endpoints when one process's `start()` fails.

## Known task-7 failures and verification

- Full Windows run: **474 passed, 7 failed, 1 skipped** (`python -m pytest -q`).
- All seven failures match the committed red tests in [execution status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md):
  timing excludes respawn; soft deadline; retry respawn via submit/readiness; readiness during
  respawn; dead-after-reply worker reuse; pipe cleanup on start failure.
- Compiler tests: 14 passed (`npm test --prefix tools`). Offline content check: 6 problems pass.
- Ruff and mypy pass. The initial sandbox run had temporary-file permission errors;
  the unrestricted rerun above eliminated all 21 setup errors.
- Linux memory-limit test skipped on Windows. Docker build/host behavior was not verified here.

## Claude's next pass

1. Add regressions and fix B-C1/B-C2; review their numerical/resource guarantees again.
2. Finish the seven existing pool fixes and B-C3; rerun lifecycle tests and the full suite.
3. Run content/compiler checks and the docs checker; keep each Markdown file <= 100 lines.
4. Update [execution status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)
   and the handoff with fix commits and evidence, then resume task 8 under R10–R13.
