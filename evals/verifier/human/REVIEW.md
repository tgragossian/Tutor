# Dev cases: review sheet (task 9, step 4)

[Verifier evaluation](../README.md) · [Spec 08](../../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md) · [R22/R23 spec](../../../docs/superpowers/specs/2026-10-19-function-input-and-domain-rewrite-design.md)

136 draft cases in [`dev.src.yaml`](dev.src.yaml), captured from real MathLive into
[`dev.jsonl`](dev.jsonl). Every case has `reviewer: 'pending'`. For each case check that the
input is something a student could type, the label is right on the stored domain, and the
rationale holds; then set `reviewer: 'tg'`. A disputed case gets a note and stays out until settled.
Labels were written from the mathematics before the verifier ran and were not changed after.

## What changed under R22 and R23

- 25 inputs with an unparenthesized function were rewritten to parenthesized LaTeX, keeping
  label and meaning (`\sec x^2` became `\sec(x^2)`). `d-lnsq-02` (`\ln\lvert x\rvert`) was
  already accepted: bars count as parentheses. Their labels were not touched.
- `d-181-05`: Thomas chose R22 option A (require parentheses). The case is now
  `(1-\sin(x))^2-\cos(x)(x+\cos(x))`, label `correct`, and the verifier agrees.
- Five new `unsupported` regression cases `d-r22-01..05` (`\sin x`, `\cos x(x+1)`,
  `\cos^2x`, `\log_2 8`, `\operatorname{sin}x`): all rejected with `unsupported_notation`.
- Edited and new cases stay `reviewer: 'pending'` for your review.

Fresh draft run (`evaluate --set dev --gate B --draft`, 2026-10-19, after R22/R23):
FA 0 of 54 (95% upper bound 6.6%) · FR 0 of 52 (95% upper bound 6.9%) · coverage 51 of 52
(98.1%) · unsupported graded correct 0 of 30 · agreement 135 of 136 (99.3%). Metrics pass
gate B; the release gate still fails because no row is reviewed.

## Disagreements (1 left of the earlier 9)

Before R22/R23: 9 disagreements (FR 2/52, coverage 43/52, agreement 122/131 on 131 cases).

- Now agree: 1 `d-181-05` (R22 option A), 2 `d-log2-01` (fixed in 832740f), 3 `d-tan-01`,
  4 `d-dtan-01`, 5 `d-csc-02`, 6 `d-cot-01` (R23 decides their trig denominators),
  7 `d-cot-03` (R23 plus the exact hole-limit check: the hole at 3pi/2 is removable, so it
  grades correct), 9 `d-lnsq-02` (R23 rewrites |x| != 0 to x != 0).
- Still disagrees: 8 `d-explog-03` ln(e^x) vs x on R. Label correct, verifier abstains
  (`domain_unproven`, marked in REVIEW-3). The spec expected R23's rule "e^u > 0
  always holds" to decide it; it does not yet. Tracked in the
  [follow-ups](../../../docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md).

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
| Unsupported notation | 16 | 8 | [REVIEW-4](REVIEW-4.md) |
| Resource limits | 7 | 5 | [REVIEW-4](REVIEW-4.md) |

Labels: 52 correct, 54 incorrect, 30 unsupported. Families: the six seed problems plus ten
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
