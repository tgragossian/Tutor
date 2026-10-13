[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 272–319. Review findings remain unresolved.

### Task 4: Trusted-answer parsing and equivalence core

**Files:**
- Create: `src/mathtutor/verify/expected.py`, `equivalence.py`, `tests/verify/test_expected.py`, `tests/verify/test_equivalence.py`

**Interfaces:**
- Produces:
  - `def parse_expected(spec: AnswerSpec) -> sympy.Expr | _Dne | tuple[sympy.Expr, ...]`
    - Uses `parse_expr` with `local_dict` holding only the spec's symbols, `fp`/`gp`, and SymPy functions.
    - Also recognises `oo`, `-oo` and `DNE`.
    - Raises `ValueError` with the offending string.
  - `def compare(student: sympy.Expr, expected: sympy.Expr, *, variable: str, domain: tuple[float, float], seed: int = 0) -> tuple[Status, str, Method]`
    - Implements §4.2 steps 1–2.
    - Free symbols other than `variable` are sampled from [-3, 3].
    - Reasons: `symbolic_equal`, `numeric_agree`, `counterexample`, `student_undefined`, `insufficient_sample_points`.
    - Step 1 goes through a private `_symbolic_equal(a, b) -> bool` (`simplify(a - b) == 0`), so tests can force the numeric path.
    - The numeric-point rule from Global Constraints applies.

- [ ] **Step 1: Write the failing tests**

```python
def test_symbolic_equal(): assert compare(sp.sin(x)**2 + sp.cos(x)**2, sp.Integer(1), variable="x", domain=(-5, 5))[0] == "correct"
def test_counterexample(): assert compare(2*x, x**2, variable="x", domain=(-5, 5)) == ("incorrect", "counterexample", "numeric")
def test_numeric_path_used_when_simplify_cant(monkeypatch):
    monkeypatch.setattr(equivalence, "_symbolic_equal", lambda a, b: False)
    assert compare(sp.sin(x)**2 + sp.cos(x)**2, sp.Integer(1), variable="x", domain=(-5, 5)) == ("correct", "numeric_agree", "numeric")
def test_sqrt_x2_not_x_on_mixed_domain():  # Review Focus 1
    assert compare(sp.sqrt(x**2), x, variable="x", domain=(-5, 5))[0] == "incorrect"
def test_student_undefined_where_expected_defined():  # Review Focus 1: student 2 ln x, expected ln(x²)
    assert compare(2*sp.log(x), sp.log(x**2), variable="x", domain=(-5, 5)) == ("incorrect", "student_undefined", "numeric")
def test_ln_x2_vs_2lnx_positive_domain(): assert compare(sp.log(x**2), 2*sp.log(x), variable="x", domain=(0.1, 5))[0] == "correct"
def test_insufficient_points():  # expected undefined on the whole domain
    assert compare(sp.sqrt(x - 10), sp.sqrt(x - 10) + 1, variable="x", domain=(-5, 5)) == ("unable_to_verify", "insufficient_sample_points", "none")
def test_abstract_symbols_sampled(): assert compare(fp*g + f*gp, gp*f + g*fp, variable="x", domain=(-5, 5))[0] == "correct"
def test_parse_expected_rejects_garbage(): pytest.raises(ValueError, parse_expected, AnswerSpec("expression", "6*x*cos(("))
def test_parse_expected_dne_and_oo(): ...
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_expected.py tests/verify/test_equivalence.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - Use `random.Random(seed)` to draw points and `mpmath.mp.dps = 50` (scoped with `mpmath.workdps(50)`).
  - Evaluate with `sp.lambdify(..., "mpmath")`.
  - A point is *expected-invalid*, and skipped, if evaluating the expected answer raises or gives a complex or non-finite value. If only the student's side fails there, that is `student_undefined`.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): trusted parsing and equivalence`.

---

<!-- End preserved source. -->
