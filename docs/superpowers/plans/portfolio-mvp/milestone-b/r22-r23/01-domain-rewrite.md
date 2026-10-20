# Task 1: R23 constraint rewrite

[R22/R23 plan](README.md) · [Spec R23](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#r23-restrictions-are-solved-on-their-inner-argument)

**Files:**
- Create: `src/mathtutor/verify/rewrite.py`
- Modify: `src/mathtutor/verify/equivalence.py` (`_exact_violations`, ~line 236)
- Test: `tests/unit/verify/test_rewrite.py`, `tests/unit/verify/test_check.py`

**Interfaces:**
- Consumes: `Constraint(kind, expr)` and `ConstraintKind` from `verify/translate.py`;
  `_trig_violations` / `_rational_violations` in `equivalence.py` (unchanged).
- Produces: `reduce_constraint(c: Constraint) -> tuple[Constraint, ...]`. Empty tuple means
  "always holds". A constraint no rule matches is returned unchanged as `(c,)`.

Rules (apply recursively to every produced constraint; `u` any expression):

| Input | Output |
|---|---|
| `nonzero` of `cos(u)` | `not_half_pi_odd(u)` |
| `nonzero` of `sin(u)` or `tan(u)` | `not_pi_multiple(u)` |
| `nonzero` of `Mul(a, b, ...)` | `nonzero` of each factor |
| `nonzero` of `Pow(b, n)`, `n` a positive Integer | `nonzero(b)` |
| any kind of `exp(u)` | `()` |
| `positive` or `nonzero` of `Abs(u)` | `nonzero(u)` |
| `nonnegative` of `Abs(u)` | `()` |

Match on the unevaluated tree (`isinstance(expr, sympy.cos)`, `expr.is_Mul`, `expr.is_Pow`,
`expr.func is sympy.exp`, `isinstance(expr, sympy.Abs)`); never call `simplify`. A rational
constant factor such as the 3 in `3·sin(x/3)` stays `nonzero(3)`; the R19 rational solver
already decides it (empty set).

- [ ] **Step 1: Write failing tests** in `test_rewrite.py` (X = real symbol `x`):
  - `test_cos_nonzero_becomes_half_pi_lattice`: `reduce_constraint(Constraint("nonzero", cos(3*X+1)))`
    `== (Constraint("not_half_pi_odd", 3*X+1),)`.
  - `test_sin_and_tan_nonzero_become_pi_lattice`: same shape for `sin(X/3)` and `tan(X/3)`.
  - `test_product_and_power_split`: `nonzero(Mul(3, sin(X/3), evaluate=False))` →
    `{nonzero(3), not_pi_multiple(X/3)}`; `nonzero(cos(X)**2)` → `(not_half_pi_odd(X),)`.
  - `test_exp_always_holds`: `()` for `positive`, `nonnegative`, `nonzero` of `exp(X)`.
  - `test_abs_reduces_to_inner_nonzero`: `positive(Abs(X))` and `nonzero(Abs(X))` →
    `(nonzero(X),)`; `nonnegative(Abs(X))` → `()`.
  - `test_unmatched_is_unchanged`: `positive(cos(X))`, `nonnegative(X - 1)`,
    `nonzero(Pow(X, Rational(1, 2)))`, `positive(Pow(Abs(X), Rational(1, 2)))` return `(c,)`.
- [ ] **Step 2:** `uv run pytest tests/unit/verify/test_rewrite.py -q` → fails (`ModuleNotFoundError`).
- [ ] **Step 3: Implement `reduce_constraint`** in `rewrite.py` (no SymPy evaluation, no imports
  from `equivalence`, to avoid a cycle).
- [ ] **Step 4:** test file passes.
- [ ] **Step 5: Wire it.** Failing tests first in `test_check.py`, through `check` with
  `expression_spec(..., Domain(intervals=[...]))`, each expected `CORRECT`:
  - `test_sin_over_cos_is_tan_on_minus_one_one` (d-tan-01): `sin x / cos x` vs `tan x` on (−1, 1).
  - `test_one_over_sin_is_csc` (d-csc-02): on (1/2, 3).
  - `test_cot_third_from_cos_over_sin` (d-cot-01): `cos(x/3)/(3 sin(x/3))` vs `cot(x/3)/3` on (0, 9).
  - `test_ln_exp_is_x` (d-explog-03): `ln(e^x)` vs `x` on ℝ.
  - `test_two_ln_abs_is_ln_square` (d-lnsq-02): `2 ln|x|` vs `ln(x^2)` on ℝ∖{0}.
  - `test_cot_irrational_hole_still_abstains` (d-cot-03): `1/(3 tan(x/3))` vs `cot(x/3)/3`
    on (0, 9) → `UNABLE_TO_VERIFY`.
  - In `test_equivalence.py`, `violation_set` raises `DomainUnproven` for
    `positive(cos(X))` on `Interval(-1, 1)` and for `positive(Abs(X)**Rational(1, 2))` on ℝ.
  - Domains are written `Domain(intervals=[("-1", "1", "open", "open")])`.
- [ ] **Step 6:** In `_exact_violations`, decide each reduced constraint with the existing
  dispatch (trig kinds → `_trig_violations`, else `_rational_violations`) and return their
  `sympy.Union` (`EmptySet` for `()`). `violation_set` keeps cross-checking the **original**
  constraint, so a wrong rewrite is caught as `DomainUnproven`.
- [ ] **Step 7:** full checks from the README pass; commit
  `feat: decide domain restrictions on their inner argument (R23)`.
