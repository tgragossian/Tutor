# R24: pre-check and regression tests

[R24 checklist](README.md) · [Approved spec](../../../../specs/2026-10-20-decimal-places-design.md)

Implemented in a76985d with failing tests first. Regressions pass in the green Linux CI run;
keep format validation and mathematical grading separate when debugging future changes.

## Tests first

- [x] For `precision: {decimals: 3}`, exact `-200/343` remains symbolic and correct.
- [x] `-0.583` proceeds to rounding and is correct; `-0.584` is incorrect by rounding.
- [x] `-0.5830`, `-0.58349`, `-0.58309`, `-0.5835`, `-0.58`, `-0.5825` and `0.5833`
  return `wrong_decimal_places`, never a correctness verdict.
- [x] Trailing zeros count from original LaTeX, even if MathJSON drops them.
- [x] LaTeX/MathJSON value disagreement abstains; it cannot produce a correct verdict.
- [x] Negative/bracketed literals retain existing standalone-decimal semantics.
- [x] Decimals inside fractions or larger expressions remain exact rationals; retain
  the eight decimal near-miss traps and existing removable-hole regressions.
- [x] Exercise multiple N values so the rule is per-problem, not hard-coded to 3.
- [x] Evaluation recognizes `wrong_decimal_places` as agreeing with `unsupported`.

a76985d records the tests-first failures and fix. Tests now enforce scoped precision while
retaining ROUND_HALF_EVEN and exact-arithmetic coverage; N = 0, 2, 3 and 4 are exercised.

## Owning modules

| Layer | Files | Responsibility |
|---|---|---|
| Input evidence | `verify/types.py`, `verify/evaluate.py`, capture tooling | preserve original decimal spelling through submission |
| Format vocabulary | `domain.py` | add `WRONG_DECIMAL_PLACES` |
| Format validation | `verify/precheck.py` | enforce N only on the scoped standalone decimal |
| Grading | `verify/check.py`, `verify/numeric.py` | preserve symbolic/rounding rules; abstain on value disagreement |
| Evaluation | `verify/evaluate.py` | include the new code in `_UNSUPPORTED_ISSUES` |

Python paths are relative to `src/mathtutor/`; tests live in `tests/unit/verify/`.
Existing submission types carry field LaTeX; no separate raw_latex field was added to them.
The web process must remain free of SymPy; preserve bounds and worker containment.

## Debugging order

1. Compare authored `raw_latex`, captured `answer.latex` and `answer.mathjson`.
2. The evaluator passes captured `answer.latex` to `SubmittedAnswer`; MathLive preserves
   the zero in `-0.5830` there as well as in `raw_latex`. `latex_decimal_places` counts it.
3. Check standalone-decimal classification before counting places; do not apply this
   rule to decimal coefficients or nested fractions.
4. Check exact value agreement before a rounding verdict. Unknown/mismatched input abstains.
5. Inspect format code and evaluator agreement separately; a correct format issue must
   not appear as a disagreement because of a missing enum mapping.
6. For changed inputs, recapture and rerun the [release checks](02-release.md); preserve human labels.
