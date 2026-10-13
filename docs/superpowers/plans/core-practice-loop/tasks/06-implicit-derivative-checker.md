[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 373–405. Review findings remain unresolved.

### Task 6: Implicit-derivative checker

**Files:**
- Create: `src/mathtutor/verify/implicit.py`, `tests/verify/test_implicit.py`
- Modify: `checkers.py`. Route `implicit_derivative` here and pass `symbols={variable, "y"}`.

**Interfaces:**
- Produces: `def check_implicit(student: sympy.Expr, expected: sympy.Expr, relation: sympy.Expr, *, variable: str, domain: tuple[float, float], seed: int = 0) -> tuple[Status, str, Method]`.
  - For each of 20 x-values, find real y with `relation(x, y) = 0`: `sympy.nsolve` from starts y ∈ {-10, -1, 0.5, 1, 10}, deduplicated.
  - Compare at every (x, y) pair using the §4.2 tolerance.
  - With fewer than 10 valid pairs → `insufficient_sample_points`.

  **Algorithm note:** a student answer must match the expected answer **at each (x, y) pair it is defined at**. For the circle example, `-x/√(25−x²)` only matches on the upper branch. It is therefore judged `incorrect`, with a counterexample on the lower branch, unless the problem restricts the domain. Encode this explicitly in a test so it is a decision, not an accident.

- [ ] **Step 1: Write the failing tests**

```python
REL = x**2 + y**2 - 25
def test_equivalent_on_curve(): assert check_implicit(-x/y, -x/y, REL, variable="x", domain=(-4, 4))[0] == "correct"
def test_wrong_sign(): assert check_implicit(x/y, -x/y, REL, variable="x", domain=(-4, 4))[0] == "incorrect"
def test_explicit_branch_rejected_on_full_curve():
    assert check_implicit(-x/sp.sqrt(25 - x**2), -x/y, REL, variable="x", domain=(-4, 4))[0] == "incorrect"
def test_curve_dependent_form_accepted(): ...   # x**2+y**2=25: student (-x*y)/(25 - x**2) vs expected -x/y → correct (equal only on the curve)
def test_no_real_points(): ...                  # relation x**2+y**2+1 → ("unable_to_verify", "insufficient_sample_points", "none")
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_implicit.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, and add one routing test in `test_checkers.py` that uses `mj("implicit_ans")` and `mj("implicit_alt")`.
- [ ] **Step 4:** Run `uv run pytest tests/verify -v`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): implicit differentiation checker`.

---

<!-- End preserved source. -->
