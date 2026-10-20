# R24: pre-check and regression tests

[R24 checklist](README.md) · [Approved spec](../../../../specs/2026-10-20-decimal-places-design.md)

Status: planned, not implemented. Keep format validation and mathematical grading separate
so a failed case can be traced to the responsible layer.

## Tests first

- [ ] For `precision: {decimals: 3}`, exact `-200/343` remains symbolic and correct.
- [ ] `-0.583` proceeds to rounding and is correct; `-0.584` is incorrect by rounding.
- [ ] `-0.5830`, `-0.58349`, `-0.58309`, `-0.5835`, `-0.58`, `-0.5825` and `0.5833`
  return `wrong_decimal_places`, never a correctness verdict.
- [ ] Trailing zeros count from original LaTeX, even if MathJSON drops them.
- [ ] LaTeX/MathJSON value disagreement abstains; it cannot produce a correct verdict.
- [ ] Negative/bracketed literals retain existing standalone-decimal semantics.
- [ ] Decimals inside fractions or larger expressions remain exact rationals; retain
  the eight decimal near-miss traps and existing removable-hole regressions.
- [ ] Exercise multiple N values so the rule is per-problem, not hard-coded to 3.
- [ ] Evaluation recognizes `wrong_decimal_places` as agreeing with `unsupported`.

Run focused tests before implementation and record their expected failures. Update tests
that assert unlimited standalone precision; retain ROUND_HALF_EVEN and exact-arithmetic tests.

## Owning modules

| Layer | Files | Responsibility |
|---|---|---|
| Input evidence | `verify/types.py`, `verify/evaluate.py`, capture tooling | preserve original decimal spelling through submission |
| Format vocabulary | `domain.py` | add `WRONG_DECIMAL_PLACES` |
| Format validation | `verify/precheck.py` | enforce N only on the scoped standalone decimal |
| Grading | `verify/check.py`, `verify/numeric.py` | preserve symbolic/rounding rules; abstain on value disagreement |
| Evaluation | `verify/evaluate.py` | include the new code in `_UNSUPPORTED_ISSUES` |

Python paths are relative to `src/mathtutor/`; tests live in `tests/unit/verify/`.
Use existing types where practical; exact implementation details follow failing tests.
The web process must remain free of SymPy; preserve bounds and worker containment.

## Debugging order

1. Compare authored `raw_latex`, captured `answer.latex` and `answer.mathjson`.
2. Check which spelling reaches `SubmittedAnswer`; at 9b2e1f2 the evaluator uses normalized
   `answer.latex`, so raw capture metadata alone does not enforce R24.
3. Check standalone-decimal classification before counting places; do not apply this
   rule to decimal coefficients or nested fractions.
4. Check exact value agreement before a rounding verdict. Unknown/mismatched input abstains.
5. Inspect format code and evaluator agreement separately; a correct format issue must
   not appear as a disagreement because of a missing enum mapping.
6. Continue with [content and release](02-release.md) after focused regressions pass.
