# Dev cases: review sheet (task 9, step 4)

[Verifier evaluation](../README.md) · [Spec 08](../../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

131 draft cases in [`dev.src.yaml`](dev.src.yaml), captured from real MathLive into
[`dev.jsonl`](dev.jsonl). Every case has `reviewer: 'pending'`. For each case check that the
input is something a student could type, the label is right on the stored domain, and the
rationale holds; then set `reviewer: 'tg'`. A disputed case gets a note and stays out until settled.
Labels were written from the mathematics before the verifier ran and were not changed after.

Draft run (`evaluate --set dev --gate B --out evals/verifier/results/dev-draft.json`):
FA 0 of 54 (95% upper bound 6.6%) · FR 2 of 52 (3.8%) · coverage 43 of 52 (82.7%) ·
unsupported graded correct 0 of 25 · agreement 122 of 131. Gate B fails on FR and coverage.

## Disagreements (9)

Two false rejects (definite `incorrect` on a `correct` label), then seven abstentions.

1. `d-181-05` `(1-\sin x)^2-\cos x(x+\cos x)`: label correct, verifier **incorrect**
   (counterexample). **Label question?** Compute Engine parses `\cos x(x+\cos x)` as
   cos(x(x + cos x)), so the tree really is a different function and the verifier is right
   about the tree. A reader of the typed field sees cos x · (x + cos x). Choose: relabel
   `incorrect` (we grade what is sent; record why), or keep `correct` and treat it as an
   input bug (e.g. reject `\cos x(...)` as ambiguous, like `e(x+1)` in R15). This is the
   trap the seed note for 3.5-181 already warns about.
2. `d-log2-01` `x^{\log_2 8}` against `x^3` on ℝ: label correct, verifier **incorrect**
   (`undefined_on_domain`). **Verifier bug?** log₂8 is exactly 3, so the function is x³ on ℝ.
   `translate._raise` deliberately requires a positive base when the exponent is not rational
   arithmetic (`Lb(8)` is not simplified to 3), so x < 0 counts as undefined and the answer is
   graded wrong rather than abstained. Counter-view for you: if x^c with a computed exponent
   is meant to be defined only for x > 0 (as with e^{c ln x}), relabel with that rationale.
3. `d-tan-01` sin x / cos x vs tan x on (−1, 1): abstain `domain_unproven`. **Verifier bug?**
   (a coverage gap, not a soundness bug). cos x ≠ 0 holds on (−1, 1) because π/2 > 1; R19's
   lattice enumeration covers Tan/Cot constraints but apparently not `nonzero` on a
   trig denominator.
4. `d-dtan-01` 1/cos²x vs sec²x on (−1, 1): abstain `domain_unproven`. **Verifier bug?**
   Same gap as 3.
5. `d-csc-02` 1/sin x vs csc x on (1/2, 3): abstain `domain_unproven`. **Verifier bug?**
   Same gap: sin x > 0 on (0, π).
6. `d-cot-01` cos(x/3) / (3 sin(x/3)) vs cot(x/3)/3 on (0, 9): abstain `domain_unproven`.
   **Verifier bug?** Same gap: sin(x/3) ≠ 0 there since 3π > 9.
7. `d-cot-03` 1/(3 tan(x/3)) vs cot(x/3)/3 on (0, 9): abstain `domain_unproven`.
   **Verifier bug?** The only hole is x = 3π/2 (irrational). It is removable: the limit is
   0, the same as the answer there. The default rule accepts it, so the label stands. Deciding
   it needs an irrational hole plus a limit, which may be out of scope for milestone B.
8. `d-explog-03` ln(eˣ) vs x on ℝ: abstain `domain_unproven`. **Verifier bug?** The
   constraint eˣ > 0 holds everywhere; the violation set is empty but is not proven.
9. `d-lnsq-02` 2 ln|x| vs ln(x²) on ℝ∖{0}: abstain `domain_unproven`. **Verifier bug?**
   |x| > 0 fails only at the excluded 0. R18 makes Abs abstain conservatively.

Not disagreements, but worth a look: `d-253-06` (−0.58349 is *correct* by the spec 02
rounding rule), `d-253-02` (the trailing zero of −0.5830 is lost in capture), and the
partial-input cases (labelled `unsupported`; see the harness note below).

## Cases by category

| Category | Cases | Spec 08 minimum | File |
|---|---:|---:|---|
| Correct but tricky forms | 34 | 15 | [REVIEW-1](REVIEW-1.md) |
| Baseline (choice a) | 1 | — | [REVIEW-1](REVIEW-1.md) |
| Typical errors | 34 | 20 | [REVIEW-2](REVIEW-2.md) |
| Domain traps | 17 | 12 | [REVIEW-3](REVIEW-3.md) |
| Near-equal perturbations | 11 | 8 | [REVIEW-3](REVIEW-3.md) |
| Decimals at rounding boundaries | 9 | 6 | [REVIEW-3](REVIEW-3.md) |
| Partial / placeholder input | 7 | 6 | [REVIEW-4](REVIEW-4.md) |
| Unsupported notation | 11 | 8 | [REVIEW-4](REVIEW-4.md) |
| Resource limits | 7 | 5 | [REVIEW-4](REVIEW-4.md) |

Labels: 52 correct, 54 incorrect, 25 unsupported. Families: the six seed problems plus ten
`inline-*` families (inline specs for holes, log/root/exp domains, and trig identities).

## Notes for the reviewer

- Seed answers: 111 is 270x⁴ + 39/(x+1)² on ℝ∖{−1}; 115 is 4 + 2/x² − 2/x³ on ℝ∖{0};
  181 is (1 − sin x)² − (x + cos x)cos x; 221 is 18x(3x² + 1)²; 253 is −200/343 to
  3 decimals; x2cosx is choice a.
- **Harness note:** `unsupported` now also agrees with `empty` and `incomplete` format issues,
  so partial input can be labelled `unsupported` (task 8 had only notation and size).
- `reviewer: 'pending'` passes the row schema (non-blank). The task 9 step-5 gate must require `tg`; it is not implemented yet.
  After review, recapture JSONL from the reviewed YAML before release evaluation.
- Chromium's renderer sometimes crashes on deeply nested roots (`d-221-26`). The capture tool
  retries on a fresh page, which is why that case has 31 levels rather than more.
