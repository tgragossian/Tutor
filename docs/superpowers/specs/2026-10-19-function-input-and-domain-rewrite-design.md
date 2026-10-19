# Function input and domain rewrites (R22, R23)

[Specs index](README.md) · [Portfolio core](2026-10-13-portfolio-core/README.md) · [Decision 0001](../../decisions/0001-delivery-verifier-attribution.md) · [Decision 0002](../../decisions/0002-mathlive-input.md) · [Review sheet](../../../evals/verifier/human/REVIEW.md)

**Status:** approved by Thomas, 2026-10-19; implemented in ea6748b..19db4ab (R23 follow-up) and the dev-case recapture commits.
Scope: milestone B, before task 10. Fixes review sheet disagreements 1 and 3–9.
Precedence: decision 0001 still wins; this amends ruling R18 and decision 0002 as stated.

## R22: function input always uses parentheses

**Why:** `\cos x(x+\cos x)` displays as cos x · (x + cos x) but Compute Engine parses
cos(x(x + cos x)) (`d-181-05`). The tree cannot show which was meant: `\cos x(x+1)` and
`\cos(x(x+1))` give the same MathJSON. Thomas chose: require parentheses, as Desmos does.

1. **Practice field (task 14).** MathLive inline shortcuts turn `sin cos tan sec csc cot ln
   log` into `\fn\left(\placeholder{}\right)`. Powers and bases sit before the parentheses:
   `\sin^2(x)`, `\log_2(8)`.
2. **Server rule (pre-check).** In submitted LaTeX, each function command, after optional
   `^...` and `_...` groups, must be followed by `(` or `\left(`. Otherwise: format issue
   `unsupported_notation` with R16 copy "Put the function's input in parentheses, like sin(x)."
   Rejects `\sin x`, `\cos x(...)`, `\cos^2x`, `\ln 2`, `\log_2 8`.
3. **Exception:** absolute-value bars (`\lvert`, `\left|`, `|`) count as the parentheses,
   so `\ln\lvert x\rvert` is accepted.
4. **Amends decision 0002:** LaTeX may also be read for this rule. It can only reject, so it
   can never make a wrong answer correct; grading still uses MathJSON only.
5. **Content:** text quoted from OpenStax (problem statements) keeps its original notation.
   LaTeX we author (expected answers, worked solutions, hints, feedback) must use
   parentheses; the content check fails the build otherwise.

## R23: restrictions are solved on their inner argument

The exact solvers of R19 are unchanged. A rewrite step runs first and replaces each
recorded constraint with equivalent constraints on its inner argument, recursively:

| Constraint | Rewritten to |
|---|---|
| cos(u) ≠ 0 | u ∉ π/2 + πℤ (`not_half_pi_odd`) |
| sin(u) ≠ 0 | u ∉ πℤ (`not_pi_multiple`) |
| tan(u) ≠ 0 | u ∉ πℤ (tan's own poles are already recorded) |
| a·b ≠ 0 | a ≠ 0 and b ≠ 0 |
| bⁿ ≠ 0, n a positive integer | b ≠ 0 |
| e^u > 0, ≥ 0 or ≠ 0 | always holds |
| \|u\| > 0 or \|u\| ≠ 0 | u ≠ 0 |
| \|u\| ≥ 0 | always holds |
| nonzero rational constant c | holds or fails exactly |

- Each rule is an exact equivalence on the reals wherever u is defined; u's own constraints
  are recorded separately by the translator, so nothing is lost.
- After rewriting, a constraint goes to the existing solvers: rational functions over ℚ
  (R19 i) or linear trig arguments on a bounded domain (R19 ii). Anything else still raises
  `DomainUnproven`. Every decided set still gets the seeded-point cross-check.
- **Amends R18:** Abs at the top of a constraint is rewritten as above. Abs or sign under a
  non-integer power still abstains.
- **Still abstains:** sign constraints on trig (cos(u) > 0) and unbounded trig domains.
- **`d-cot-03`** (hole at 3π/2) is now proven: R23 decides its other constraint, and the
  existing exact hole-limit check shows the hole is removable (limit 0 = the answer there).
- Inverse trig (arcsin u needs −1 ≤ u ≤ 1) fits this table but waits for topic expansion.

## Dev cases

- Recapture through real MathLive after editing `dev.src.yaml`. Labels never change to match
  the verifier; the input changes only because R22 changed what a student can submit.
- The 25 cases whose input has an unparenthesized function (the bare-function scan finds 26;
  `d-lnsq-02` uses absolute-value bars, which R22 accepts) get the parenthesized form, with
  the same label and meaning (`\sec x^2`, meant as sec(x²), becomes `\sec(x^2)`).
  `d-181-05` becomes `(1-\sin(x))^2-\cos(x)(x+\cos(x))`, label `correct`.
- New `unsupported` regression cases: `\sin x`, `\cos x(x+1)`, `\cos^2x`, `\log_2 8`, and `\operatorname{sin}x` (the operatorname/mathrm bypass, closed in 098b7ba).
- Every edited or new case stays `reviewer: 'pending'` for Thomas.

## Testing and evidence

- Failing test first for each R22 pattern (rejects and accepts), each R23 rule, and the
  still-abstains list (cos(x) > 0 on ℝ; |u| under x^(1/2)).
- Content check test: an authored answer with `\sin x` fails the build.
- Actual draft result (136 cases): FA 0/54, FR 0/52, coverage 52/52, agreement 136/136.
  All nine disagreements agree; 8 (`d-explog-03`) needed 19db4ab (typed e^x is Power(e, x)).
- Full Python and tool suites, ruff, mypy and the docs checker pass before each commit.
