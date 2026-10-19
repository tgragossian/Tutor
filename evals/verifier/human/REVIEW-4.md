# Dev cases review: Partial, unsupported and resource

[Review index](REVIEW.md)

One line per case: id · input as typed · label · rationale · verifier verdict.
A ✗ marks a disagreement (discussed in the index).

## Partial / placeholder input (7)

- `d-111-15` · `270x^4+\frac{39}{\placeholder{}}` (typed keys) · unsupported · Submitted mid-typing: the fraction 39/[ ] has an empty denominator slot -> incomplete. · format: incomplete
- `d-115-16` · `4+\frac{2}{\placeholder{}}` (typed keys) · unsupported · Submitted mid-typing: 4 + 2/[ ] has an empty denominator slot -> incomplete. · format: incomplete
- `d-181-13` · `(1-\sin(x))^{\placeholder{}}-(x+\cos(x))\cos(x)` · unsupported · Exponent slot left empty (a placeholder) -> incomplete. · format: incomplete
- `d-221-22` · `18x\left(3x^2+1\right)^{}` (typed keys) · unsupported · Submitted with the outer exponent slot still empty -> incomplete. · format: incomplete
- `d-221-23` · `x^{}` (typed keys) · unsupported · x^[ ]: MathLive sends x^{} (MathJSON just x), so only the LaTeX shows it is incomplete. · format: incomplete
- `d-253-30` · `` · unsupported · Empty field submitted -> empty. · format: empty
- `d-253-31` · `-\frac{200}{\placeholder{}}` (typed keys) · unsupported · Submitted mid-typing: -200/[ ] has an empty denominator slot -> incomplete. · format: incomplete

## Unsupported notation (16)

- `d-111-14` · `\begin{pmatrix}270x^4&\frac{39}{(x+1)^2}\end{pmatrix}` · unsupported · Terms entered in a matrix (virtual-keyboard slip); a Matrix is outside the allowlist. · format: unsupported_notation
- `d-115-14` · `4+\frac{2}{x^2}-\frac{2}{x^3}+C` · unsupported · A +C habit from antiderivatives; C is only allowed for antiderivative items (spec 02). · format: unsupported_notation
- `d-115-15` · `f'(x)=4+\frac{2}{x^2}-\frac{2}{x^3}` · unsupported · An equation f'(x) = ... rather than an expression; Equal and f are outside the allowlist. · format: unsupported_notation
- `d-221-19` · `3u^2\cdot6x` · unsupported · Left in terms of the decomposition variable u; only the item variable x is allowed. · format: unsupported_notation
- `d-221-20` · `y'=18x(3x^2+1)^2` · unsupported · An equation y' = ... rather than an expression; Equal and y are outside the allowlist. · format: unsupported_notation
- `d-221-21` · `\frac{d}{dx}(3x^2+1)^3` · unsupported · Restates the question with the d/dx operator; a derivative operator is not an answer form. · format: unsupported_notation
- `d-253-22` · `-200(t+1)^{-3}` · unsupported · The velocity function v(t), not its value at t = 6; t is not the item variable. · format: unsupported_notation
- `d-253-23` · `\infty` · unsupported · Infinity is a limit token, not a numeric answer (outside the core allowlist). · format: unsupported_notation
- `d-253-24` · `\mathrm{DNE}` · unsupported · DNE is a limit token (deferred kind), not a numeric answer. · format: unsupported_notation
- `d-253-25` · `-0.583\,\mathrm{m/s}` · unsupported · Units typed after the number; unit symbols are outside the allowlist. · format: unsupported_notation
- `d-csc-01` [expected `\csc(x)` on (1/2, 3)] · `\sin^{-1}(x)` · unsupported · sin^-1(x) is ambiguous (arcsin vs 1/sin); inverse trig is deferred, so unsupported_notation. · format: unsupported_notation
- `d-r22-01` [expected `\sin(x)`] · `\sin x` · unsupported · R22: function input must be parenthesized. · format: unsupported_notation
- `d-r22-02` [expected `\cos(x)(x+1)`] · `\cos x(x+1)` · unsupported · R22: function input must be parenthesized. · format: unsupported_notation
- `d-r22-03` [expected `\cos^2(x)`] · `\cos^2x` · unsupported · R22: function input must be parenthesized. · format: unsupported_notation
- `d-r22-04` [expected `\log_2(8)`] · `\log_2 8` · unsupported · R22: function input must be parenthesized. · format: unsupported_notation
- `d-r22-05` [expected `\sin(x)`] · `\operatorname{sin}x` · unsupported · R22: function input must be parenthesized (also when the name is written with operatorname). · format: unsupported_notation

## Resource limits (7)

- `d-221-24` · `x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x+x` · unsupported · A sum of 201 terms x: 202 MathJSON nodes, over the 200-node bound -> input_too_large. · format: input_too_large
- `d-221-25` · `(3x^2+1)^{1001}` · unsupported · Exponent 1001 exceeds the 1000 bound (and degree 2002 exceeds 200) -> input_too_large. · format: input_too_large
- `d-221-26` · `\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{\sqrt{x}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}` · unsupported · 31 nested square roots of x: depth 31, over the depth-30 bound -> input_too_large. · format: input_too_large
- `d-253-26` · `10^{10^{10}}` · unsupported · Tower: the inner 10^10 exceeds the exponent bound 1000 -> input_too_large. · format: input_too_large
- `d-253-27` · `1234567890123456789012345678901234567890` · unsupported · 40-digit integer, over the 30-digit bound -> input_too_large. · format: input_too_large
- `d-253-28` · `-0.5830903790087463556851311953352769679300` · unsupported · 40 significant digits, over the 30-digit decimal bound -> input_too_large (even though it rounds right). · format: input_too_large
- `d-253-29` · `2^{2^{2^{2^2}}}` · unsupported · 2^65536 has 19729 digits, over the 1000-digit constant bound -> input_too_large. · format: input_too_large
