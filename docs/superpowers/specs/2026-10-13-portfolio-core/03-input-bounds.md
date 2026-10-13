# 03 — Input bounds and translation

[Contracts index](README.md)

## Where it runs

- **The web process** does cheap structural validation only: byte size, JSON shape, node count and depth.
- **Everything that builds SymPy objects runs inside the verifier worker**, under its deadline ([05](05-verifier-execution.md)). This includes the cost estimate and translation.

## Structural bounds (checked before building anything)

| Bound | Limit | Violation → |
|---|---|---|
| Request body | 16 KB | 413 |
| Nodes | 200 | `input_too_large` |
| Depth | 30 | `input_too_large` |
| Function arity | exactly as the allowlist declares | `unsupported_notation` |
| Integer literal | ≤ 30 digits | `input_too_large` |
| Decimal literal | ≤ 30 significant digits; no scientific exponent beyond ±30 | `input_too_large` |
| Symbol names | the item's variable only (plus `C` / abstract functions for kinds that allow them) | `unsupported_notation` |

## Cost bound before construction (fixes computed-power blowups)

- The translator walks the tree **bottom-up**, computing a conservative estimate for each subtree:
  - `const_digits`: an upper bound on the digit count if the subtree is a constant
  - `degree`: an upper bound on the polynomial degree in the variable
- **`Power(a, b)` with constant `b`:**
  - Reject if |b| exceeds 1000.
  - Reject if `const_digits(a) × |b|` exceeds 1000 digits.
  - Reject if `degree(a) × |b|` exceeds 200.
- **`Power` with a non-constant exponent** (e.g. `x^x`, `2^x`) is allowed, but `b` must itself satisfy the bounds. It is never expanded.
- **Nested towers are rejected through the estimate**: `10^(10^10)` → the inner subtree has `const_digits` 11 and value 10^10, which exceeds the bound on b.
- **Construction never evaluates:** nodes are built with `evaluate=False` and evaluated only by the equivalence code after the cost check passes.
- Any violation → `input_too_large`.

## Allowlist (core milestones)

| Category | Allowed |
|---|---|
| Numbers | JSON integers, decimals and `{"num": "..."}` (read with `Decimal`, kept as exact `Rational`), `Rational` |
| Constants | `Pi`; `ExponentialE`, and raw `"e"` meaning the same |
| Arithmetic | `Add`, `Subtract`, `Negate`, `Multiply`, `InvisibleOperator` (= product), `Divide`, `Power`, `Sqrt`, `Root` |
| Trig | `Sin`, `Cos`, `Tan`, `Sec`, `Csc`, `Cot`; inverses (`Arcsin`, `Apply(InverseFunction(Sin))`) deferred until a topic needs them |
| Other | `Ln`; `Log` (1 argument = base 10; 2 = explicit base); `Lb` (base 2); `Exp`, `Abs` |
| Wrappers | `Delimiter` with one argument, unwrapped. A `Delimiter` holding a `Sequence` (a list) is `unsupported_notation` |

- **Real-root rule:** `Root(a, n)` with odd integer `n` means the **real** n-th root (`sympy.real_root`). `Sqrt(a)` and even roots are principal roots, and their domain constraints are recorded.
- **Variables** are created as `Symbol(name, real=True)`.
- **Unknown heads, symbols or shapes → `Rejected("unsupported_notation")`.** Head names come from the raw (`form: 'raw'`) fixtures in [ADR 0002](../../../decisions/0002-mathlive-input.md). An `InvisibleOperator` whose first factor is a non-variable letter followed by a `Delimiter` (e.g. `f(2x)`) is function application, not a product, and is unsupported in the core kinds.

## Output

- `translate(tree, ctx) -> Translated`, where `Translated = (expr: sympy.Expr, constraints: tuple[Constraint, ...])`.
- **The constraints come from the raw tree, collected before any cancellation:**
  - every denominator ≠ 0
  - every `Ln` / `Log` argument > 0
  - every even-root / `Sqrt` argument ≥ 0
  - every `Tan` / `Sec` argument ≠ π/2 + kπ
  - every `Cot` / `Csc` argument ≠ kπ
  - every power with a negative or fractional exponent: base constraints as above
- [04](04-equivalence.md) uses these constraints to decide definedness and removable holes.

## Tests required (milestone B)

- Hypothesis: random trees built from allowed heads, unknown heads, junk strings and numbers. The result is always a `Translated` value or a `Rejected`, never any other exception.
- Towers and wide expressions near each bound, from both sides of the limit.
- Every captured fixture key translates as expected.
