# 04 — Equivalence and domains

[Contracts index](README.md) · [Decision 0001](../../../decisions/0001-delivery-verifier-attribution.md)

## Verdicts

The `status` is one of `correct`, `incorrect` or `unable_to_verify`, with a `reason` code and a `method` of `symbolic`, `domain`, `refutation`, `rounding`, `exact` or `none`.

## Algorithm for `expression` (and exact `numeric`)

Inputs:
- `S`, `cS`: the student's expression and constraints
- `E`, `cE`: the expected expression and constraints
- domain `D` and the `strict` flag

1. **Prove equality of the formulas.**
   - Compute `d = S − E` and try these strategies in order, each with a time budget inside the worker deadline:
     - `cancel` / `together`
     - `simplify`
     - `trigsimp`
     - `expand_trig` then `simplify`
     - `powsimp(force=False)`
     - `radsimp`
   - If any strategy returns exactly `0`, the formulas are equal → go to step 2.
   - If none does, go to step 3.
2. **Check the domain.**
   - For each student constraint in `cS`, compute the set of points in `D` where it is violated: `solveset(violation, x, D)`.
   - **Empty set** → fine.
   - **Finite set H** → these are holes.
     - With `strict`: → `incorrect`, reason `undefined_on_domain`.
     - Otherwise each h ∈ H must be **removable**: `limit(S, x, h)` from both sides must exist, be finite, and equal `E(h)`, where `E` is defined at h. If all holes are removable → `correct`. If any is not → `incorrect`, reason `pole_on_domain`.
   - **Interval, `ConditionSet`, or unknown** → `unable_to_verify`, reason `domain_unproven`. Exception: if the set contains a whole subinterval where `E` is defined, the student's expression is missing part of the domain → `incorrect`, reason `undefined_on_domain`. This case requires a certified point from step 3's refutation procedure.
   - All constraints pass → `correct`, method `symbolic`.
3. **Try to refute.**
   - Pick up to 20 rational points from `D` with a fixed seed, plus the endpoints and midpoints of each interval, skipping excluded points.
   - At each point evaluate `E` and `S` with **interval arithmetic** (`mpmath.iv`, 60 digits).
   - A **certified counterexample** is a point where:
     - `E`'s enclosure is real and finite, **and**
     - either `S` is provably undefined there (a constraint is violated exactly, checked with exact rationals) → reason `student_undefined`,
     - or the enclosures of `S` and `E` are **disjoint** → reason `counterexample`.
   - Any certified counterexample → `incorrect`, method `refutation`.
4. **Otherwise** → `unable_to_verify`, reason `not_proven`.
   - The student sees "We couldn't check this automatically."
   - The attempt is logged so missing proof strategies can be found and added.

## Consequences (become required tests)

| Expected | Student | Domain | Verdict |
|---|---|---|---|
| `x` | `x + 1/1000000000` | ℝ | `incorrect` (counterexample; enclosures are disjoint at 60 digits) |
| `x + 1` | `(x²−1)/(x−1)` | ℝ | `correct` (removable hole at 1) |
| `x + 1` | `(x²−1)/(x−1)` | ℝ, strict | `incorrect` (`undefined_on_domain`) |
| `ln(x²)` | `2 ln x` | ℝ \ {0} | `incorrect` (`student_undefined` at a negative point) |
| `2 ln x` | `ln(x²)` | (0, ∞) | `correct` |
| `x` | `√(x²)` | ℝ | `incorrect` (counterexample at x < 0) |
| `1/x` | `1/x` with a pole at 0 inside D | content error | the loader rejects it (expected undefined on D) |
| `sin²x + cos²x` | `1` | ℝ | `correct` (`simplify`) |

**Why interval arithmetic:** an enclosure is a rigorous bound, so the refutation is certified rather than a judgement within a tolerance. The `x + 10⁻⁹` case is rejected because the enclosures don't overlap at 60 digits. In general, a perturbation smaller than the working precision can only abstain, never be accepted.

## `numeric` and `choice`

- **Decimal:** the rounding rule in [02](02-answer-contracts.md), method `rounding`.
- **Exact:** steps 1–4 with a constant domain. Domain checks are trivial.
- **`choice`:** id equality, method `exact`.

## Not provided

- **No tolerance-based acceptance anywhere.**
- **No equivalence over complex numbers.** Every variable is real.
- **Unsupported families** (beyond what `solveset` can decide on the constraints) abstain. They are never guessed.
