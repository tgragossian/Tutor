# 0003: function input requires parentheses

[Decisions index](README.md) · [Spec](../superpowers/specs/2026-10-19-function-input-and-domain-rewrite-design.md) · [Amends 0002](0002-mathlive-input.md)

Status: accepted by Thomas, 2026-10-19. Amends decision 0002: the submitted LaTeX is also read
for the reject-only rule below. Grading still uses MathJSON only.

## Why

`\cos x(x+\cos x)` displays as cos x times (x + cos x), but Compute Engine parses it as
cos(x(x + cos x)). The tree cannot say which was meant: `\cos x(x+1)` and `\cos(x(x+1))`
give the same MathJSON. Thomas chose to require parentheses, as Desmos does (option A).

## The rule (R22)

- Function commands: `\sin \cos \tan \sec \csc \cot \ln \log \lg \lb \exp`.
- The same names written as `\operatorname{sin}` or `\mathrm{sin}` (MathLive also writes a
  typed operatorname as `\operatorname{\mathrm{sin}}`) are treated exactly like `\sin`.
  Names outside the list (`\mathrm{d}`, `\mathrm{e}`, `\operatorname{lcm}`) are not touched.
- After the command and any `^...` and `_...` groups, the next token must be an opener:
  `(` or `\left(`, or an absolute-value opener `|`, `\lvert`, `\vert`, `\left|`,
  `\left\lvert`, `\left\vert`. Whitespace and thin spaces (`\,` `\;` `\!` `\ `) are skipped.
- Accepted: `\sin(x)`, `\sin^2(x)`, `\log_2(8)`, `\sin\left(x\right)`, `\ln\lvert x\rvert`.
- Rejected: `\sin x`, `\cos x(x+1)`, `\cos^2x`, `\ln 2`, `\log_2 8`, `\operatorname{sin}x`.
- Letters after the command end it, so `\sinh`, `\cosh`, `\lnot` and `\left` never match.

## Copy

A rejected input is a format issue `unsupported_notation` with the detail
"Put the function's input in parentheses, like sin(x)."

## Consequences

- The practice field's inline shortcuts and keyboard buttons insert the parenthesized form
  (task 14), so a student seldom meets the message.
- The rule can only reject, never accept, so it cannot make a wrong answer correct.
- Authored content (expected answers, solutions, hints, feedback) must use parentheses; the
  content check fails the build otherwise. Quoted OpenStax statement text keeps its notation.
- Dev cases were recaptured under the rule; see the
  [review sheet](../../evals/verifier/human/REVIEW.md).
