# Decimal answers use exactly N places (R24)

[Specs index](README.md) · [Spec 02](2026-10-13-portfolio-core/02-answer-contracts.md) · [Decision 0001](../../decisions/0001-delivery-verifier-attribution.md) · [Decision 0002](../../decisions/0002-mathlive-input.md) · [Review sheet](../../../evals/verifier/human/REVIEW.md)

**Status:** rule approved by Thomas, 2026-10-20, during the task 9 case review.
Not yet implemented; implementation waits until the review is finished.
Precedence: decision 0001 still wins; this amends spec 02 "Decimal precision" as stated.

## Why

Spec 02 grades any decimal by rounding it to N places, with no minimum or maximum, because
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

The seven relabelled cases cite R24 and stay `reviewer: 'pending'` for Thomas.

## Implementation (after the review)

- Add `WRONG_DECIMAL_PLACES` to `FormatIssueCode` and to `_UNSUPPORTED_ISSUES` in
  `src/mathtutor/verify/evaluate.py`; check places in the pre-check.
- Failing test first for each row of the rule table, the LaTeX/MathJSON mismatch, and a
  decimal inside a fraction (still exact).
- Update the problem 253 statement and compiled content, and the REVIEW.md notes on
  `d-253-02` and `d-253-06`.
- Recapture the dev set, run gate B, and record the before and after metrics.
