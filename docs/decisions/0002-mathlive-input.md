# 0002: MathLive input capture

[Decisions index](README.md)

Status: proposed — awaiting Thomas's approval.

Evidence: `tests/fixtures/mathjson/captured.json`, produced by `npm run capture --prefix tools` in
real Chromium 156 (cases in `tools/capture/cases.json`). Snippets below are copied from it.

## 1. Versions and the parse call

- `mathlive` **0.111.1**, `@cortex-js/compute-engine` **0.151.0**, `playwright` 1.64.0,
  `yaml` 2.9.1, all pinned exactly in `tools/package.json`.
- 0.111.1 is used although it is under two weeks old: it contains the XSS fixes.
- MathLive 0.111.1 declares **no** Compute Engine dependency and bundles none. We therefore import
  `ComputeEngine` ourselves and attach it: `MathfieldElement.computeEngine = new ComputeEngine()`.
- 0.151.0 was the newest release when MathLive 0.111.1 shipped (2026-10-09); 0.152.0 is not used.
- Call: `MathfieldElement.computeEngine.parse(mf.getValue(), {form: 'raw'}).json`.
- Option name: **`form: 'raw'`**, which is the typed option in the installed `.d.ts`.
  `{canonical: false}` is a deprecated alias in 0.151.0 and produced identical output on every
  case tried. The spec's `{canonical: false}` still works but should be written `{form: 'raw'}`.

## 2. Number encoding: the fallback applies

- `dec_0780` (`0.780`): LaTeX stays `0.780`, but MathJSON is the bare number `0.78`. **The
  trailing zero is lost**, in raw and canonical form, setValue and typed (`typed_dec_0780`).
- `toMathJson` options (`shorthands`, `digits`, `metadata`) do not restore it. `2.50` gives `2.5`.
- **Decision: spec 02's fallback.** Do not enforce a minimum number of decimal places
  (`too_few_decimals` is dropped for milestone A). Any decimal is graded by rounding to N places.
- Decimals are bare JSON numbers (`0.785`, `["Divide",0.5,"x"]`) or `{"num": "..."}`: the number
  object appears for long literals. `long_int` is `{"num":"1234567890123456789012345678901234567890"}`.
  Python must parse with `parse_float=Decimal`/`parse_int` to avoid float rounding.
- Constants differ by form: raw gives `"e"` and `"Pi"`; canonical gives `"ExponentialE"`.
  **The translator must accept raw `e` as `ExponentialE`** (`pi_e`, `exp_x2`).

## 3. Heads for the allowlist (raw MathJSON)

| Construct | Case | Raw MathJSON |
|---|---|---|
| fraction, minus | `frac_pi_4`, `neg_half` | `["Divide","Pi",4]`, `["Negate",["Divide",1,2]]` |
| subtraction | `rational_fn` | `["Subtract",["Power","x",2],1]` |
| implicit product | `implicit_mult`, `six_x_cos` | `["InvisibleOperator",2,"Pi","x"]` |
| power | `neg_power`, `frac_power` | `["Power","x",["Negate",2]]`, `["Power","x",["Divide",3,2]]` |
| trig | `sin2x`, `sec2`, `tan_x`, `cot_x` | `["Power",["Sin","x"],2]`, `["Sec","x"]` ... |
| sin of 2x | `sin_of_2x` | `["Sin",["InvisibleOperator",2,"x"]]` |
| inverse trig | `arcsin` | `["Arcsin","x"]` |
| `\sin^{-1}` | `sin_inv` | `["Apply",["InverseFunction","Sin"],"x"]` (canonical: `Arcsin`) |
| roots | `sqrt_x`, `cuberoot` | `["Sqrt","x"]`, `["Root","x",3]` |
| absolute value | `abs_x` | `["Abs","x"]` |
| logs | `ln_x`, `log_x` | `["Ln","x"]`, `["Log","x"]` (base 10) |
| `\log_2` | `log2_x` | `["Lb","x"]` (canonical: `["Log","x",2]`) |
| exponential | `exp_x2`, `exp_fn` | `["Power","e",["Power","x",2]]`, `["Exp","x"]` |
| parentheses | probe `(x+1)^2` | `["Power",["Delimiter",["Add","x",1]],2]` |

- `\log_{10} x` gives `["Log","x"]`, `\log_{e} x` gives `["Log","x","e"]`, `\lg x` gives
  `["Log","x",10]`. The translator must treat `Log` with one argument as base 10.
- The translator needs extra raw heads beyond spec 03: `InvisibleOperator`, `Lb` (base 2),
  `Apply`/`InverseFunction`, `Delimiter`. Parenthesised groups arrive wrapped in `Delimiter`.
- Raw is chosen deliberately: canonical reorders terms and folds `-1/2` into `Rational`.

## 4. Format-issue shapes

| Case | LaTeX out | Raw MathJSON | Code |
|---|---|---|---|
| `empty` | `""` | `"Nothing"` | `empty` |
| `incomplete` (`x^{\placeholder{}}`) | same | **`"x"`** | see below |
| `typed_pow_empty` (typed `x^`) | `x^{}` | **`"x"`** | see below |
| `typed_frac_empty` (typed `1/`) | `\frac{1}{\placeholder{}}` | `["Divide",1,["Error","'missing'"]]` | `incomplete` |
| `matrix` | `\begin{pmatrix}1&2\end{pmatrix}` | `["Matrix",["List",["List",1,2]]]` | `unsupported_notation` |
| `huge_pow` | `10^{10^{10}}` | `["Power",10,["Power",10,10]]` | `input_too_large` (cost) |
| `long_int` (40 digits) | same | `{"num":"1234567890123456789012345678901234567890"}` | `input_too_large` |

- **Finding: placeholders vanish.** `\placeholder{}` in an exponent, and an empty `x^{}`, parse to the
  bare `"x"`; other positions give `Error` or `Nothing`. A half-typed `x^` would be graded as `x`.
- Resolution (proposed): the client must refuse to submit while the field holds a `\placeholder`
  or an empty `^{}`/`_{}`/`{}` group (a string check on `mf.getValue()`, not a parser), and the
  server pre-check keeps rejecting `Error` and `Nothing`. This needs a spec 02 amendment.
- `set_pts`: `["Delimiter",["Sequence",["Negate",1],1],"','"]`; `inf`: `"PositiveInfinity"`; `dne`: `"DNE"`.

## 5. Typed input versus setValue

- Typed input produces the same MathJSON as `setValue` of equivalent LaTeX in every case:
  `typed_sin` and `sin_of_2x` are both `["Sin",["InvisibleOperator",2,"x"]]`; `typed_sqrt` is
  `["Sqrt","x"]`; `typed_frac` is `["Divide",1,"x"]`; `typed_pow` is `["Add",["Power","x",2],1]`.
- Only the LaTeX differs: typed `sin(2x)` gives `\sin\left(2x\right)`. `typed_` fixtures rule.

## 6. Deferred kinds (recorded only)

- `f_of_2x`: `["f",["InvisibleOperator",2,"x"]]`. The argument is distinguishable from the bare `x`.
- `product_rule`: `f'(x)g(x)+f(x)g'(x)` raw is
  `["Add",["InvisibleOperator",["Apply",["Derivative","f",1],"x"],"g",["Delimiter","x"]], ...]`.
- `antideriv_c`: `["Add",["Divide",["Power","x",3],3],"C"]`, with `C` a plain symbol.

## 7. Decision

- MathJSON from `computeEngine.parse(latex, {form: 'raw'}).json` represents all in-scope inputs
  faithfully. **No custom LaTeX parser is needed.**
- Exception to resolve at approval: placeholder/empty-group loss (section 4), handled by a
  client string check plus a spec 02 amendment, not by a parser.
- Consequences: spec 02 option becomes `form: 'raw'`; `too_few_decimals` is dropped.
