# Dev cases review: Domain, near-equal and rounding

[Review index](REVIEW.md)

One line per case: id · input as typed · reviewed label · rationale · measured verdict.
Verdicts are from [dev-b.json](../results/dev-b.json), the reviewed non-draft run at b5ad4b2.

## Domain traps (17)

- `d-115-12` · `\frac{4x^5+2x^3-2x^2}{x^5}` · correct · An extra factor x top and bottom; its only hole is x = 0, which the domain already excludes. · correct: proven
- `d-221-13` · `\frac{18x^2(3x^2+1)^2}{x}` · correct · Hole at x = 0 only; it is removable (limit 0 = the answer at 0), so the default rule accepts it. · correct: proven
- `d-221-14` · `18\sqrt{x^2}(3x^2+1)^2` · incorrect · sqrt(x^2) = |x|, not x: at x = -1 it gives 288 vs -288. · incorrect: counterexample
- `d-221-15` · `\frac{18x(3x^2+1)^3}{3x^2+1}` · correct · Cancels to the answer; the denominator 3x^2 + 1 has no real zero, so no hole at all. · correct: proven
- `d-hole-01` [expected `x+1`] · `\frac{x^2-1}{x-1}` · correct · (x^2-1)/(x-1) = x + 1 for x != 1; the hole at 1 is removable (limit 2 = 1 + 1), default rule. · correct: proven
- `d-hole-02` [expected `x+1` strict] · `\frac{x^2-1}{x-1}` · incorrect · Strict domain R: the student expression is undefined at x = 1, which is in the domain. · incorrect: undefined_on_domain
- `d-hole-03` [expected `x+1`] · `\frac{x^2+x}{x}` · correct · (x^2 + x)/x = x + 1 for x != 0; the hole at 0 is removable (limit 1 = 0 + 1). · correct: proven
- `d-lnsq-01` [expected `\ln(x^2)` x ≠ 0] · `2\ln(x)` · incorrect · On R \ {0}: 2 ln x is undefined for every x < 0, where ln(x^2) is defined. · incorrect: student_undefined
- `d-lnsq-02` [expected `\ln(x^2)` x ≠ 0] · `2\ln\lvert x\rvert` · correct · ln(x^2) = ln(|x|^2) = 2 ln|x| for every x != 0. · correct: proven
- `d-lnsq-03` [expected `2\ln(x)` on (0, inf)] · `\ln(x^2)` · correct · On (0, inf): ln(x^2) = 2 ln x. · correct: proven
- `d-sqsq-01` [expected `x`] · `\sqrt{x^2}` · incorrect · sqrt(x^2) = |x|: at x = -1 it is 1, not -1. · incorrect: counterexample
- `d-sqsq-02` [expected `x` on [0, inf)] · `\sqrt{x^2}` · correct · On [0, inf): sqrt(x^2) = |x| = x. · correct: proven
- `d-sqsq-03` [expected `\lvert x\rvert`] · `\sqrt{x^2}` · correct · sqrt(x^2) = |x| for every real x. · correct: proven
- `d-explog-01` [expected `x`] · `e^{\ln(x)}` · incorrect · On R: e^(ln x) is undefined for every x <= 0, a whole interval where x is defined. · incorrect: undefined_on_domain
- `d-explog-02` [expected `x` on (0, inf)] · `e^{\ln(x)}` · correct · On (0, inf): e^(ln x) = x. · correct: proven
- `d-explog-03` [expected `x`] · `\ln(e^x)` · correct · e^x > 0 for every real x, so ln(e^x) is defined on R and equals x. · correct: proven
- `d-cot-03` [expected `\frac{1}{3}\cot(\frac{x}{3})` on (0, 9)] · `\frac{1}{3\tan(\frac{x}{3})}` · correct · Equal to cot(x/3)/3 except at x = 3pi/2, where tan(x/3) is undefined; that hole is removable (limit 0 = the answer there). · correct: proven

## Near-equal perturbations (11)

- `d-111-12` · `270x^4+\frac{39}{(x+1)^2}+0.000000001` · incorrect · Differs from the answer by the constant 10^-9 everywhere; no tolerance applies. · incorrect: counterexample
- `d-111-13` · `270.0000001x^4+\frac{39}{(x+1)^2}` · incorrect · Differs by 10^-7 x^4, nonzero for every x != 0. · incorrect: counterexample
- `d-115-13` · `4+\frac{2}{x^2}-\frac{2.000001}{x^3}` · incorrect · Differs by 10^-6/x^3, nonzero on the whole domain; the inner decimal is an exact rational. · incorrect: counterexample
- `d-181-11` · `(1-\sin(x))^2-(x+\cos(x))\cos(x)+10^{-9}` · incorrect · Differs by the constant 10^-9 everywhere. · incorrect: counterexample
- `d-181-12` · `(1-\sin(x))^2-(1.000001x+\cos(x))\cos(x)` · incorrect · Differs by 10^-6 x cos x, nonzero at x = 1. · incorrect: counterexample
- `d-221-16` · `18x(3x^2+1)^2+10^{-9}` · incorrect · Differs by the constant 10^-9 everywhere. · incorrect: counterexample
- `d-221-17` · `18.000000001x(3x^2+1)^2` · incorrect · Differs by 10^-9 x(3x^2 + 1)^2, nonzero for x != 0. · incorrect: counterexample
- `d-221-18` · `18x(3x^2+1.0000001)^2` · incorrect · Inner constant off by 10^-7; at x = 1 the value differs by about 18 * 2 * 4 * 10^-7. · incorrect: counterexample
- `d-253-19` · `0.5833` · unsupported · R24: 4 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-20` · `-\frac{200}{343}+0.000000001` · incorrect · Not a plain decimal, so graded exactly: differs from -200/343 by 10^-9. · incorrect: counterexample
- `d-253-21` · `-\frac{200.000001}{343}` · incorrect · Inner decimal is exact: differs from -200/343 by 10^-6/343. · incorrect: counterexample

## Decimals at rounding boundaries (9)

- `d-253-01` · `-0.583` · correct · -200/343 = -0.583090...; rounds to -0.583 at 3 places, same as the student. · correct: rounded_match
- `d-253-02` · `-0.5830` · unsupported · R24: 4 decimal places; exactly 3 requested. Format issue, not incorrect. The trailing zero survives in raw_latex, not MathJSON. · format: wrong_decimal_places
- `d-253-03` · `-0.5835` · unsupported · R24: 4 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-04` · `-0.58` · unsupported · R24: 2 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-05` · `-0.5825` · unsupported · R24: 4 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-06` · `-0.58349` · unsupported · R24: 5 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-07` · `-0.584` · incorrect · Rounded the wrong way: -0.58309 rounds to -0.583. · incorrect: rounded_mismatch
- `d-253-08` · `-0.58309` · unsupported · R24: 5 decimal places; exactly 3 requested. Format issue, not incorrect. · format: wrong_decimal_places
- `d-253-09` · `-\frac{200}{343}` · correct · The exact value v(6) = -200/(6+1)^3; checked symbolically. · correct: proven
