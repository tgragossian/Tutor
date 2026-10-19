# Task 3: Allowlist translator and cost bound

[Milestone B plan](../README.md) · [Spec 03](../../../../specs/2026-10-13-portfolio-core/03-input-bounds.md) · [ADR 0002](../../../../../decisions/0002-mathlive-input.md)

**Status (2026-10-19):** Complete: b5c05b9..ee4f4bf; R14/R15 refine powers/input; B-C2 fixed in b7f23ad.
See [rulings](../02-execution-rulings.md) and [execution status](../03-execution-status.md); checked steps include recorded replacements.

**Files:**
- Create: `src/mathtutor/verify/translate.py`, `tests/unit/verify/test_translate.py`, `tests/unit/verify/test_translate_fuzz.py`
- Modify: `pyproject.toml` (`uv add sympy mpmath`; `uv add --dev hypothesis`)

**Interfaces:**
- Consumes: `FormatIssueCode` (domain), `check_structure` (task 2), `mj(key)` fixtures.
- Produces:
  - `@dataclass(frozen=True) class Constraint: kind: Literal["nonzero", "positive", "nonnegative", "not_half_pi_odd", "not_pi_multiple"]; expr: sympy.Expr`
  - `@dataclass(frozen=True) class Translated: expr: sympy.Expr; constraints: tuple[Constraint, ...]`
  - `@dataclass(frozen=True) class Rejected: code: FormatIssueCode; detail: str`
  - `@dataclass(frozen=True) class TranslateContext: variable: str = "x"`
  - `def translate(tree: JsonValue, ctx: TranslateContext) -> Translated | Rejected` — never raises.
  - `VARIABLE_ASSUMPTIONS = {"real": True}`; symbols are `sympy.Symbol(name, real=True)`.

- [x] **Step 1: Write the failing tests** (one table test over the captured fixtures, plus bounds and fuzz).

```python
X = sympy.Symbol("x", real=True)
CASES = {  # fixture key -> expected expr (compared with sympy.simplify(a - b) == 0) or Rejected code
    "x_plain": X, "six_x_cos": 6*X*cos(3*X**2), "sin_of_2x": sin(2*X), "sec2": sec(X)**2,
    "frac_power": X**Rational(3, 2), "neg_power": X**-2, "cuberoot": real_root(X, 3),
    "ln_x": log(X), "log_x": log(X, 10), "lg_x": log(X, 10), "log2_x": log(X, 2), "loge_x": log(X),
    "exp_x2": exp(X**2), "exp_fn": exp(X), "pi_e": pi + E, "abs_x": Abs(X), "paren_sq": (X + 1)**2,
    "implicit_mult": 2*pi*X, "neg_half": Rational(-1, 2), "dec_inside": Rational(1, 2)/X,
    "matrix": "unsupported_notation", "set_pts": "unsupported_notation", "f_of_2x": "unsupported_notation",
    "arcsin": "unsupported_notation", "sin_inv": "unsupported_notation", "inf": "unsupported_notation",
    "dne": "unsupported_notation", "antideriv_c": "unsupported_notation", "huge_pow": "input_too_large",
    "long_int": "input_too_large",
}
def test_captured_fixture_translates(key): ...          # parametrized over CASES; every captured key appears once
def test_constraints_come_from_raw_tree(): t = translate(mj("rational_fn"), CTX); assert Constraint("nonzero", X - 1) in t.constraints
def test_constraint_kinds(): ...   # ln → positive; sqrt → nonnegative; tan/sec → not_half_pi_odd; cot/csc → not_pi_multiple; x^-2 → nonzero x
def test_power_exponent_bound_both_sides(): ...  # x^1000 ok? no: degree 1000 > 200 → too large; x^200 ok, x^201 too large
def test_const_digits_bound(): ...   # 10^1000 has 1001 digits → too large; 10^999 ok
def test_nonconstant_exponent_allowed(): assert isinstance(translate(["Power", 2, "x"], CTX), Translated)
def test_other_symbol_rejected(): assert translate(["Add", "x", "y"], CTX).code == "unsupported_notation"
def test_no_evaluation_during_build(): ...      # translate(["Power", 2, 1000]) builds Pow(2, 1000, evaluate=False)
@given(trees())   # hypothesis strategy: allowed heads, unknown heads, junk strings, ints, {"num": ...}
def test_translate_never_raises(tree): assert isinstance(translate(tree, CTX), (Translated, Rejected))
```

- [x] **Step 2:** Run `uv run pytest tests/unit/verify/test_translate.py -q`. Expected: FAIL (module missing).
- [x] **Step 3: Implement `translate`.** One recursive descent over the raw tree, after `check_structure` passes, computing for every subtree `(expr, const_digits | None, degree | None)` bottom-up:
  - Heads and meanings exactly as spec 03's allowlist and ADR 0002 §3: `"e"`/`ExponentialE` → `E`; `Pi`; one-argument `Log` = base 10; `Lb` = base 2; `Log(a, b)` = base b; `Root(a, n)` odd n → `real_root`; `Delimiter` with one argument unwraps; `InvisibleOperator` = product unless its first factor is a non-variable letter followed by a `Delimiter` (function application → `unsupported_notation`).
  - Numbers: int → `Integer`; `{"num": s}` → `Rational(Decimal(s))` exactly.
  - Build every node with `evaluate=False`. Never call `sympify`.
  - Power cost rule (spec 03): reject if |b| > 1000, or `const_digits(a) × |b|` > 1000, or `degree(a) × |b|` > 200, using the integer value of a constant exponent; a non-constant exponent must itself pass the bounds and is not expanded.
  - Collect constraints from the raw tree while descending (denominators, `Ln`/`Log` arguments, `Sqrt`/even `Root` arguments, `Tan`/`Sec`, `Cot`/`Csc`, negative or fractional powers).
  - Any unexpected exception inside → `Rejected("unsupported_notation", <type name>)` (the fuzz test pins this).
- [x] **Step 4:** Run `uv run pytest tests/unit/verify -q` with the fuzz test (`max_examples=500` in CI). Expected: PASS.
- [x] **Step 5: Commit** `feat: allowlist MathJSON translator with cost bounds and domain constraints`.
