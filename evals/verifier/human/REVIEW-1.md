# Dev cases review: Correct forms

[Review index](REVIEW.md)

One line per case: id · input as typed · label · rationale · verifier verdict.
A ✗ marks a disagreement (discussed in the index).

## Correct but tricky forms (34)

- `d-111-01` · `\frac{39}{(x+1)^2}+270x^4` · correct · Same two terms, reordered. · correct: proven
- `d-111-02` · `270x^4+39(x+1)^{-2}` · correct · 39(x+1)^(-2) = 39/(x+1)^2; the only restriction, x != -1, is already excluded. · correct: proven
- `d-111-03` · `\frac{270x^4(x+1)^2+39}{(x+1)^2}` · correct · Common denominator: 270x^4(x+1)^2/(x+1)^2 + 39/(x+1)^2; same restriction x != -1. · correct: proven
- `d-111-04` · `270x^4+\frac{39}{x^2+2x+1}` · correct · x^2+2x+1 = (x+1)^2, zero only at the excluded x = -1. · correct: proven
- `d-111-05` · `3\left(90x^4+\frac{13}{(x+1)^2}\right)` · correct · Factor 3 pulled out: 3*90x^4 = 270x^4 and 3*13 = 39. · correct: proven
- `d-111-06` · `3\left(18x^4+\frac{13}{x+1}\right)+3x\left(72x^3-\frac{13}{(x+1)^2}\right)` · correct · Unsimplified product rule: 54x^4 + 39/(x+1) + 216x^4 - 39x/(x+1)^2 = 270x^4 + 39[(x+1)-x]/(x+1)^2. · correct: proven
- `d-115-01` · `\frac{4x^4+2x^2-2x}{x^4}` · correct · The OpenStax key form; dividing through by x^4 gives 4 + 2/x^2 - 2/x^3; hole only at excluded 0. · correct: proven
- `d-115-02` · `4+2x^{-2}-2x^{-3}` · correct · Negative exponents: 2x^-2 = 2/x^2, 2x^-3 = 2/x^3. · correct: proven
- `d-115-03` · `\frac{4x^3+2x-2}{x^3}` · correct · (4x^3 + 2x - 2)/x^3 = 4 + 2/x^2 - 2/x^3. · correct: proven
- `d-115-04` · `\frac{(12x^2-2)x^2-(4x^3-2x+1)(2x)}{x^4}` · correct · Unsimplified quotient rule: numerator 12x^4 - 2x^2 - 8x^4 + 4x^2 - 2x = 4x^4 + 2x^2 - 2x. · correct: proven
- `d-115-05` · `\frac{2(2x^3+x-1)}{x^3}` · correct · 2(2x^3 + x - 1) = 4x^3 + 2x - 2, as in d-115-03. · correct: proven
- `d-181-01` · `(1-\sin(x))^2-x\cos(x)-\cos^2(x)` · correct · Second term distributed: (x + cos x)cos x = x cos x + cos^2 x. · correct: proven
- `d-181-02` · `1-2\sin(x)+\sin^2(x)-x\cos(x)-\cos^2(x)` · correct · Fully expanded: (1 - sin x)^2 = 1 - 2 sin x + sin^2 x. · correct: proven
- `d-181-03` · `(1-\sin(x))(1-\sin(x))-(x+\cos(x))\cos(x)` · correct · Product rule u'v + uv' left unsquared: (1 - sin x)(1 - sin x) = (1 - sin x)^2. · correct: proven
- `d-181-04` · `1-2\sin(x)-\cos(2x)-x\cos(x)` · correct · Expanded, with sin^2 x - cos^2 x = -cos 2x (double angle). · correct: proven
- `d-181-05` · `(1-\sin(x))^2-\cos(x)(x+\cos(x))` · correct · cos(x) times (x + cos(x)): the answer with the factor moved first. (Originally typed without parentheses; R22 resolution, option A.) · correct: proven
- `d-221-01` · `162x^5+108x^3+18x` · correct · (3x^2+1)^2 = 9x^4 + 6x^2 + 1; times 18x gives 162x^5 + 108x^3 + 18x. · correct: proven
- `d-221-02` · `3(3x^2+1)^2\cdot6x` · correct · Chain rule left unsimplified: 3u^2 * 6x with u = 3x^2 + 1. · correct: proven
- `d-221-03` · `18x\left(9x^4+6x^2+1\right)` · correct · Square expanded inside: (3x^2 + 1)^2 = 9x^4 + 6x^2 + 1. · correct: proven
- `d-221-04` · `2x(9x^2+3)^2` · correct · (9x^2 + 3)^2 = 9(3x^2 + 1)^2, so 2x * 9(3x^2 + 1)^2 = 18x(3x^2 + 1)^2. · correct: proven
- `d-221-05` · `(3x^2+1)^2\cdot18x` · correct · Factors reordered with an explicit dot. · correct: proven
- `d-221-06` · `18x\sqrt{(3x^2+1)^4}` · correct · sqrt((3x^2 + 1)^4) = |(3x^2 + 1)^2| = (3x^2 + 1)^2 since 3x^2 + 1 > 0 for all real x. · correct: proven
- `d-253-10` · `-\frac{200}{7^3}` · correct · 7^3 = 343. · correct: proven
- `d-253-11` · `\frac{-200}{343}` · correct · Sign in the numerator: -200/343. · correct: proven
- `d-253-12` · `-200(6+1)^{-3}` · correct · v(t) = -200(t+1)^-3 evaluated at t = 6, unsimplified: -200/343. · correct: proven
- `d-253-13` · `-\frac{200}{(6+1)^3}` · correct · (6+1)^3 = 343. · correct: proven
- `d-dtan-01` [expected `\sec^2(x)` on (-1, 1)] · `\frac{1}{\cos^2(x)}` · correct · d/dx tan x on (-1, 1): sec^2 x = 1/cos^2 x; cos x > 0 there. · correct: proven
- `d-dtan-02` [expected `\sec^2(x)` on (-1, 1)] · `1+\tan^2(x)` · correct · Pythagorean identity 1 + tan^2 x = sec^2 x; tan is defined on (-1, 1). · correct: proven
- `d-tan-01` [expected `\tan(x)` on (-1, 1)] · `\frac{\sin(x)}{\cos(x)}` · correct · tan x = sin x / cos x by definition; cos x > 0 on (-1, 1). · correct: proven
- `d-cot-01` [expected `\frac{1}{3}\cot(\frac{x}{3})` on (0, 9)] · `\frac{\cos(\frac{x}{3})}{3\sin(\frac{x}{3})}` · correct · d/dx ln(sin(x/3)) on (0, 9): cot(x/3)/3 = cos(x/3)/(3 sin(x/3)); sin(x/3) > 0 there (3pi > 9). · correct: proven
- `d-cot-04` [expected `\frac{1}{3}\cot(\frac{x}{3})` on (0, 9)] · `\frac{1}{3}\cot(\frac{x}{3})` · correct · The answer with the factor 1/3 in front of cot(x/3). · correct: proven
- `d-log2-01` [expected `x^3`] · `x^{\log_2(8)}` · correct · log_2 8 = 3 exactly, so x^(log_2 8) = x^3 for every real x. · correct: proven
- `d-negpow-01` [expected `-\frac{2}{x^3}` x ≠ 0] · `-2x^{-3}` · correct · d/dx x^-2 = -2x^-3 = -2/x^3 on R \ {0}. · correct: proven
- `d-csc-02` [expected `\csc(x)` on (1/2, 3)] · `\frac{1}{\sin(x)}` · correct · csc x = 1/sin x; sin x > 0 on (1/2, 3). · correct: proven

## Baseline (1)

- `d-x2cosx-01` · choice a · correct · Choice a = 2x cos x - x^2 sin x, the product rule result. · correct: choice_match
