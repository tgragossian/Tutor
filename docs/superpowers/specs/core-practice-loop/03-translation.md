[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 160–181. Review findings remain unresolved.

## 4. Verifier

### 4.1 Translation (untrusted input)

- The input is MathJSON from MathLive. The translator walks the tree and builds SymPy objects **only** from an allowlist:
  - integers, decimals and rationals
  - the problem's variable(s); `y` for implicit problems
  - declared abstract functions
  - `Add`, `Subtract`, `Negate`, `Multiply`, `Divide`, `Power`, `Sqrt`, `Root`
  - `Sin`, `Cos`, `Tan`, `Sec`, `Csc`, `Cot` and their inverses
  - `Ln`, `Log` (base 10 or given base), `Exp`, `Abs`
  - `Pi`, `ExponentialE`, `PositiveInfinity`, `NegativeInfinity`
  - the `DNE` token
  - `List` / `Set` for `point_set`
- **Limits:**
  - max 200 nodes and depth 30
  - integer literals at most 30 digits
  - exponent literals bounded to |n| ≤ 1000
- **Never** call `sympify`, `parse_expr` or `eval` on student input.
- Expected answers are trusted and parsed with `parse_expr` at load time.
- A rejection yields `unable_to_verify` with reason `unsupported_notation` or `input_too_large`.

<!-- End preserved source. -->
