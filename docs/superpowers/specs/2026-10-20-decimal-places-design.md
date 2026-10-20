# Decimal answers use exactly N places (R24)

[Specs index](README.md) · [Spec 02](2026-10-13-portfolio-core/02-answer-contracts.md) · [Decision 0001](../../decisions/0001-delivery-verifier-attribution.md) · [Decision 0002](../../decisions/0002-mathlive-input.md) · [Review sheet](../../../evals/verifier/human/REVIEW.md)

**Status:** rule approved by Thomas, 2026-10-20, during the task 9 case review.
Implemented with failing tests first in a76985d; Thomas reviewed all 136 cases in 9b2e1f2.
Reviewed gate B and CI pass; [checklist/evidence](../plans/portfolio-mvp/milestone-b/r24/README.md).
Precedence: decision 0001 still wins; this amends spec 02 "Decimal precision" as stated.

## Why

The original spec 02 graded any decimal by rounding it to N places, without place limits:
MathJSON drops trailing zeros (decision 0002: `0.780` arrives as `0.78`). Thomas wants the
instruction to mean what it says: "round to 3 decimal places" means 3 places. `-0.5830` has
four, even though it is equal in value. The raw LaTeX keeps the zero (`d-253-02` captures
`raw_latex: "-0.5830"`), so the number of places is observable.

## Scope

Only `numeric` problems whose statement explicitly requests N decimal places
(`precision: {decimals: N}`). This is not a universal decimal-place cap.

## Rule

| Student answer | Result |
|---|---|
| Exact expression (e.g. `-\frac{200}{343}`) | allowed; graded symbolically, unchanged ([04](2026-10-13-portfolio-core/04-equivalence.md)) |
| Standalone decimal with exactly N places | correct iff it equals the expected value rounded to N places (ROUND_HALF_EVEN, unchanged) |
| Standalone decimal with any other number of places | format issue `wrong_decimal_places`, not `incorrect`; not graded |

- The message asks for an exact expression or N decimal places; it never says right or wrong.
- Too few or too many places are treated alike, whatever the value (`-0.58`, `-0.5835`).
- Places are counted from the raw LaTeX literal. If the LaTeX and the MathJSON disagree on
  the value, abstain.
- Problem statements with `decimals` say: "Give an exact answer or round to N decimal places."

## Not changed

- **Decimals inside expressions** stay exact rationals (spec 02), with no universal cap.
  Near-miss traps such as `270.0000001x^4` remain `incorrect`: students do not type them, and
  the exact rule already rejects them by proof.
- **Removable holes** (decision 0001): derivative problems keep the default, so a provably
  removable hole is ignored (`d-221-13`, `d-hole-01`, `d-hole-03`, `d-cot-03` stay correct).
  Problems that assess domain or range set `strict_domain`: there, any point where the typed
  expression is undefined, including nested denominators such as 1/tan, makes the answer wrong.

## Dev cases (problem 253, N = 3)

| Case | Input | Before | After |
|---|---|---|---|
| d-253-01 | −0.583 | correct | correct |
| d-253-07 | −0.584 | incorrect | incorrect |
| d-253-09 | −200/343 | correct | correct |
| d-253-02, -06, -08 | −0.5830, −0.58349, −0.58309 | correct | unsupported |
| d-253-03, -04, -05, -19 | −0.5835, −0.58, −0.5825, 0.5833 | incorrect | unsupported |

The seven relabelled cases cite R24 and are now `reviewer: 'tg'` in 9b2e1f2.
All 136 rows are reviewed: 49 correct, 50 incorrect, 37 unsupported; b5ad4b2 captures match source.

## Implementation and evidence

- a76985d adds `WRONG_DECIMAL_PLACES`, the pre-check and evaluator mapping, with tests first.
  LaTeX/MathJSON disagreement abstains; decimals inside expressions remain exact.
- Problem 253's statement and compiled content now explicitly request 3 decimal places.
- b5ad4b2 recaptures reviewed YAML. [dev-b.json](../../../evals/verifier/results/dev-b.json)
  (e995438) records non-draft gate B: FA 0/50 (95% upper bound 7.1%), FR 0/49,
  coverage 49/49, unsupported accepts 0/37, agreement 136/136; all seven R24 cases agree.
- 8a0bb40 enforces the dev gate in CI; all jobs pass after d673400's Linux test cleanup fix.
  See [result/CI evidence](../../../evals/verifier/results/README.md). `dev-draft.json` is historical.
