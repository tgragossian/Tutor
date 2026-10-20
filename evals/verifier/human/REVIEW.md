# Dev cases: review sheet (task 9, step 4)

[Verifier evaluation](../README.md) · [Spec 08](../../../docs/superpowers/specs/2026-10-13-portfolio-core/08-verifier-evaluation.md) · [R22/R23 spec](../../../docs/superpowers/specs/2026-10-19-function-input-and-domain-rewrite-design.md)

**2026-10-20:** task 9 complete. Thomas reviewed all 136 source rows in 9b2e1f2;
b5ad4b2 recaptures [`dev.src.yaml`](dev.src.yaml) into [`dev.jsonl`](dev.jsonl) with all `tg`.
[dev-b.json](../results/dev-b.json) records non-draft gate B: FA 0/50 (95% upper bound 7.1%),
FR 0/49 (7.3%), coverage 49/49, unsupported accepts 0/37 (9.4%), agreement 136/136.
[Result and CI evidence](../results/README.md): all three jobs pass; the dev gate is enforced.
Labels follow the mathematics and approved input contract, never verifier outcomes.

## R24 and review completion

- [R24](../../../docs/superpowers/specs/2026-10-20-decimal-places-design.md) is implemented in a76985d:
  numeric problems explicitly requesting N places require exactly N on standalone decimals.
  Other lengths produce `wrong_decimal_places`, not incorrect. Exact expressions are allowed.
- No universal decimal cap; expression decimals remain exact. Removable-hole rules are unchanged.
- `d-253-02/03/04/05/06/08/19` are reviewed `unsupported`; `d-sqsq-02` now includes zero.
- `d-253-02`: MathJSON loses the zero, but `raw_latex: "-0.5830"` preserves four places.
  `d-253-06`: `-0.58349` has five places, so R24 requires a format issue despite old rounding.
- All seven R24 labels now agree with `wrong_decimal_places`; the closed-endpoint case also agrees.
  Child-sheet verdicts come from `dev-b.json`. [Completed checklist](../../../docs/superpowers/plans/portfolio-mvp/milestone-b/r24/README.md).

## Historical changes under R22 and R23

- 25 inputs with an unparenthesized function were rewritten to parenthesized LaTeX, keeping
  label and meaning (`\sec x^2` became `\sec(x^2)`). `d-lnsq-02` (`\ln\lvert x\rvert`) was
  already accepted: bars count as parentheses. Their labels were not touched.
- `d-181-05`: Thomas chose R22 option A (require parentheses). The case is now
  `(1-\sin(x))^2-\cos(x)(x+\cos(x))`, label `correct`, and the verifier agrees.
- Five new `unsupported` regression cases `d-r22-01..05` (`\sin x`, `\cos x(x+1)`,
  `\cos^2x`, `\log_2 8`, `\operatorname{sin}x`): all rejected with `unsupported_notation`.
- Inline-spec LaTeX (authored) follows R22 too; captured trees are unchanged.
- Those cases were pending at capture; Thomas has now reviewed every source row.

Historical draft run (`evaluate --set dev --gate B --draft`, 2026-10-19, after R22/R23 and 19db4ab):
FA 0 of 54 (95% upper bound 6.6%) · FR 0 of 52 (95% upper bound 6.9%) · coverage 52 of 52
(100%) · unsupported graded correct 0 of 30 · agreement 136 of 136. Metrics pass gate B;
that run preceded human review and R24 and is superseded by the reviewed release above.

## Disagreements (none left of the earlier 9)

Before R22/R23: 9 disagreements (FR 2/52, coverage 43/52, agreement 122/131 on 131 cases).
All now agree: 1 `d-181-05` (R22 option A), 2 `d-log2-01` (fixed in 832740f), 3 `d-tan-01`,
4 `d-dtan-01`, 5 `d-csc-02`, 6 `d-cot-01` (R23 decides their trig denominators),
7 `d-cot-03` (R23 plus the exact hole-limit check: the hole at 3pi/2 is removable, so it
grades correct), 8 `d-explog-03` (ln(e^x) = x on R, label correct as Thomas confirmed;
19db4ab makes typed e^x count as always positive), 9 `d-lnsq-02` (|x| != 0 becomes x != 0).

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

Reviewed source labels: 49 correct, 50 incorrect, 37 unsupported. Families: the six seed problems plus ten
`inline-*` families (inline specs for holes, log/root/exp domains, and trig identities).

## Notes for the reviewer

- Seed answers: 111 is 270x⁴ + 39/(x+1)² on ℝ∖{−1}; 115 is 4 + 2/x² − 2/x³ on ℝ∖{0};
  181 is (1 − sin x)² − (x + cos x)cos x; 221 is 18x(3x² + 1)²; 253 is −200/343 to
  3 decimals; x2cosx is choice a.
- **Harness note:** `unsupported` now also agrees with `empty` and `incomplete` format issues,
  so partial input can be labelled `unsupported` (task 8 had only notation and size).
- The release reviewer gate requires `tg` (bdb1710); CI enforces the dev gate since 8a0bb40.
  `dev-draft.json` is historical; all current captures and the release result are reviewed.
- Chromium's renderer sometimes crashes on deeply nested roots (`d-221-26`). The capture tool
  retries on a fresh page, which is why that case has 31 levels rather than more.
