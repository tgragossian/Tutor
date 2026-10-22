# What the verifier accepts

[Verifier docs](README.md) · [Spec 03: input bounds](../superpowers/specs/2026-10-13-portfolio-core/03-input-bounds.md) · [Spec 04: equivalence](../superpowers/specs/2026-10-13-portfolio-core/04-equivalence.md)

Students type answers in a MathLive field; the browser sends its raw MathJSON tree. A
SymPy-based checker in a separate worker process grades it. "Correct" always means a
**symbolic proof**; numeric sampling can only show an answer is wrong.

## Notation it understands

| Kind | Allowed |
|---|---|
| Numbers | integers, decimals (kept exact, never as floats), fractions |
| Constants | π, e |
| Arithmetic | + − × ÷, powers, square roots, n-th roots (odd roots are real roots: ∛(−8) = −2) |
| Trig | sin, cos, tan, sec, csc, cot |
| Logs and others | ln, log (base 10, or an explicit base), lb (base 2), exp, absolute value |
| Grouping | parentheses |

The problem's own variable (usually x) is the only letter allowed, and it is real.

Anything else is rejected as **unsupported notation** before grading, with a message,
and it never uses up a try. That includes inverse trig, other letters, function names
like `f(2x)`, lists, and integrals or derivatives typed as symbols. `\sin^{-1}(x)` gets
"Did you mean arcsin(x) or 1/sin(x)?" since it is ambiguous.

**Function input needs parentheses:** `\sin x` and `\cos x\,(x+1)` are rejected with
"Put the function's input in parentheses, like sin(x)" (ruling R22). Without that rule,
`\cos x(x+1)` would parse as cos of a product.

## Size limits (checked before any math runs)

Request body 16 KB; 200 nodes; depth 30; integers up to 30 digits; decimals up to 30
significant digits. Powers are cost-estimated before they are built: an exponent above
1000, a constant over 1000 digits or a polynomial degree over 200 is rejected as
**input too large**. Towers like 10^(10^10) are caught this way.

## How grading decides

1. **Prove** student − expected = 0 with a fixed sequence of SymPy simplifications, each
   with a time budget.
2. **Check the domain.** Every denominator, log argument, even root and tan/sec/cot/csc
   argument in the student's answer is recorded before anything cancels. If the answer is
   undefined at isolated points of the problem's domain, those must be removable holes
   (the limit matches), unless the problem is strict. Example: `(x²−1)/(x−1)` for `x+1`
   on ℝ is correct; `2 ln x` for `ln(x²)` on ℝ∖{0} is incorrect.
3. **Refute.** If no proof is found, the answer and the expected answer are evaluated at
   up to 20 seeded rational points with 60-digit interval arithmetic. If the two ranges
   are disjoint at any point, the answer is **incorrect**. This certifies the answer is wrong;
   it is not a tolerance.
4. **Otherwise abstain:** `unable_to_verify` ("We couldn't check this automatically").
   It never counts as wrong, never uses a try, and Skip stays available.

**Numeric answers** that ask for decimals must round to the expected value at the stated
places (e.g. 4 decimal places); the wrong number of places is a format message, not a
wrong answer. Exact numeric answers use the proof path above. **Multiple choice** is an id match.

There is no tolerance-based acceptance anywhere, and no complex numbers.

## When it abstains

- No proof strategy closes the gap and no counterexample is found (`not_proven`).
- The set where the student's answer is undefined is an interval or something SymPy cannot
  decide (`domain_unproven`).
- The 3-second deadline is reached.

Separately, the worker pool (1 worker by default, `MATHTUTOR_POOL_SIZE`) has a queue of 8 and a
2-second queue wait; when the queue is full the reply is "busy, try again", not a verdict.

## Known limitations

- **Inverse trig** (arcsin and others) is not supported yet; no live topic needs it.
- **Slow wrong answers to nested trig:** a wrong answer to something like `sin(cos 7x)`
  can reach the 3-second deadline and return `unable_to_verify` instead of `incorrect`
  ([follow-ups](../superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md)).
- **Only three topics** are live (basic derivative rules, trig derivatives, chain rule).
  Implicit differentiation, limits and integrals come with later topics.
- Deeply nested roots can crash Chromium's MathLive capture in tests (browser limitation).

## Safety wording

Untrusted input never reaches `eval`, `sympify` or `parse_expr`; the allowlist translator
is the only place SymPy objects are built. Running the checker in a separate process with a
deadline and a memory cap (`RLIMIT_AS`, Linux) is **resource containment, not a security
sandbox**. The allowlist is the security boundary.
