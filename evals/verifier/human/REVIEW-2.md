# Dev cases review: Typical errors

[Review index](REVIEW.md)

One line per case: id · input as typed · label · rationale · verifier verdict.
A ✗ marks a disagreement (discussed in the index).

## Typical errors (34)

- `d-111-07` · `270x^4+39` · incorrect · Seed misconception: d/dx[39x/(x+1)] taken as 39. At x = 1: 309 vs 270 + 39/4. · incorrect: counterexample
- `d-111-08` · `270x^4+\frac{39}{x+1}` · incorrect · Quotient rule skipped (denominator not squared). At x = 1: 270 + 19.5 vs 270 + 9.75. · incorrect: counterexample
- `d-111-09` · `270x^4-\frac{39}{(x+1)^2}` · incorrect · Sign slip from the quotient-rule numerator taken as x-(x+1). At x = 0: -39 vs 39. · incorrect: counterexample
- `d-111-10` · `270x^5+\frac{39}{(x+1)^2}` · incorrect · Power-rule exponent not lowered (54x^5 -> 270x^5). At x = 2: 8640 vs 4320 in the first term. · incorrect: counterexample
- `d-111-11` · `3\left(72x^3-\frac{13}{(x+1)^2}\right)` · incorrect · Product of the derivatives (3x)'g'(x) instead of the product rule. At x = 0: -39 vs 39. · incorrect: counterexample
- `d-115-06` · `4-\frac{2}{x^2}+\frac{2}{x^3}` · incorrect · Both power-rule signs flipped. At x = 2: 3.75 vs 4.25 (x = 1 happens to agree). · incorrect: counterexample
- `d-115-07` · `\frac{12x^2-2}{2x}` · incorrect · Quotient of the derivatives f'/g'. At x = 1: 5 vs 4. · incorrect: counterexample
- `d-115-08` · `4+\frac{2}{x^2}-\frac{1}{x^3}` · incorrect · d/dx x^-2 = -2x^-3; the coefficient 2 was dropped. At x = 1: 5 vs 4. · incorrect: counterexample
- `d-115-09` · `\frac{(12x^2-2)x^2+(4x^3-2x+1)(2x)}{x^4}` · incorrect · Quotient rule with + instead of -. At x = 1: 16 vs 4. · incorrect: counterexample
- `d-115-10` · `\frac{(4x^3-2x+1)(2x)-(12x^2-2)x^2}{x^4}` · incorrect · Quotient-rule numerator in the wrong order: the negative of the answer. At x = 1: -4 vs 4. · incorrect: counterexample
- `d-115-11` · `4+\frac{2}{x}-\frac{2}{x^2}` · incorrect · Exponents not lowered: -2x^-1 -> 2x^-1 and x^-2 -> -2x^-2. At x = 2: 4.5 vs 4.25. · incorrect: counterexample
- `d-181-06` · `(1-\sin(x))^2+(x+\cos(x))\cos(x)` · incorrect · Seed misconception: d/dx(-sin x) taken as +cos x. At x = 0: 2 vs 0. · incorrect: counterexample
- `d-181-07` · `-(1-\sin(x))\cos(x)` · incorrect · Product of the derivatives u'v' = (1 - sin x)(-cos x). At x = 0: -1 vs 0. · incorrect: counterexample
- `d-181-08` · `(1-\sin(x))^2-(x+\cos(x))\sin(x)` · incorrect · d/dx(1 - sin x) taken as -sin x. At x = 0: 1 vs 0. · incorrect: counterexample
- `d-181-09` · `(1+\sin(x))(1-\sin(x))-(x+\cos(x))\cos(x)` · incorrect · d/dx cos x taken as +sin x; differs by 2 sin x(1 - sin x). At x = -pi/2: -4. · incorrect: counterexample
- `d-181-10` · `(1-\sin(x))^2` · incorrect · Second product-rule term dropped. At x = 0: 1 vs 0. · incorrect: counterexample
- `d-221-07` · `3(3x^2+1)^2` · incorrect · Seed misconception: inner derivative 6x missing. At x = 1: 48 vs 288. · incorrect: counterexample
- `d-221-08` · `18x(3x^2+1)^3` · incorrect · Outer exponent not lowered. At x = 1: 1152 vs 288. · incorrect: counterexample
- `d-221-09` · `6x(3x^2+1)^2` · incorrect · Outer factor 3 from the power rule dropped. At x = 1: 96 vs 288. · incorrect: counterexample
- `d-221-10` · `3(3x^2+1)^2\cdot6` · incorrect · Inner derivative taken as 6 instead of 6x. At x = 2: 3042 vs 6084 (x = 1 happens to agree). · incorrect: counterexample
- `d-221-11` · `(6x)^3` · incorrect · Inner function differentiated, then cubed. At x = 1: 216 vs 288. · incorrect: counterexample
- `d-221-12` · `18x(3x^2+1)` · incorrect · Square lost. At x = 1: 72 vs 288. · incorrect: counterexample
- `d-253-14` · `-\frac{200}{49}` · incorrect · Seed misconception: exponent not lowered, -200(t+1)^-2 at t = 6. -4.08 vs -0.583. · incorrect: counterexample
- `d-253-15` · `0.583` · incorrect · Sign dropped (speed, not velocity): +0.583 vs -0.583. · incorrect: rounded_mismatch
- `d-253-16` · `-\frac{100}{343}` · incorrect · Factor 2 from the power rule dropped: half the answer. · incorrect: counterexample
- `d-253-17` · `-\frac{200}{216}` · incorrect · Used t = 6 for t + 1 (6^3 = 216): -0.926 vs -0.583. · incorrect: counterexample
- `d-253-18` · `\frac{100}{49}` · incorrect · Position s(6) = 100/7^2 given instead of velocity. · incorrect: counterexample
- `d-x2cosx-02` · choice b · incorrect · Seed misconception: (cos x)' taken as +sin x. · incorrect: choice_mismatch
- `d-x2cosx-03` · choice c · incorrect · Seed misconception: product of the derivatives, -2x sin x. · incorrect: choice_mismatch
- `d-x2cosx-04` · choice d · incorrect · Seed misconception: cos x treated as a constant, second term dropped. · incorrect: choice_mismatch
- `d-dtan-03` [expected `\sec^2x` on (-1, 1)] · `\sec(x^2)` · incorrect · sec(x^2) instead of (sec x)^2. At x = 1/2: sec(1/4) = 1.032 vs sec^2(1/2) = 1.298. · incorrect: counterexample
- `d-dtan-04` [expected `\sec^2x` on (-1, 1)] · `-\csc^2(x)` · incorrect · Confused with d/dx cot x: negative wherever defined, while sec^2 x >= 1. · incorrect: counterexample
- `d-cot-02` [expected `\frac{1}{3}\cot(\frac{x}{3})` on (0, 9)] · `\cot(\frac{x}{3})` · incorrect · Inner derivative 1/3 missing: three times the answer, nonzero at x = 1. · incorrect: counterexample
- `d-negpow-02` [expected `-\frac{2}{x^3}` x ≠ 0] · `-2x^{-1}` · incorrect · Exponent raised instead of lowered (-2 + 1). At x = 1: -2 vs -2, at x = 2: -1 vs -1/4. · incorrect: counterexample
