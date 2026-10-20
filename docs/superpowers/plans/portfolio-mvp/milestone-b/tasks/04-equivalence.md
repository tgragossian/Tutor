# Task 4: Equivalence — proof, domain, removable holes

[Milestone B plan](../README.md) · [Spec 04](../../../../specs/2026-10-13-portfolio-core/04-equivalence.md) · [Decision 0001](../../../../../decisions/0001-delivery-verifier-attribution.md)

**Status (2026-10-19):** Complete: ee4f4bf..dbeea51; R17–R19 replace broad solveset acceptance with conservative proofs.
See [rulings](../02-execution-rulings.md) and [execution status](../03-execution-status.md); checked steps include recorded replacements.

**Files:**
- Create: `src/mathtutor/verify/equivalence.py`, `tests/unit/verify/test_equivalence.py`

**Interfaces:**
- Consumes: `Translated`, `Constraint` (task 3); `Domain` (content schema); `Verdict`, `VerdictReason`, `Method` (task 2).
- Produces:
  - `def to_sympy_set(domain: Domain) -> sympy.Set` — union of `Interval`s minus `FiniteSet(exclude)`.
  - `@dataclass class Budget: deadline: float` (a `time.monotonic()` value) with `def remaining(self) -> float`.
  - `def prove_equal(s: Expr, e: Expr, budget: Budget) -> bool` — strategies in spec order on `d = s − e`: `cancel(together(d))`, `simplify`, `trigsimp`, `simplify(expand_trig(d))`, `powsimp(d, force=False)`, `radsimp`; `True` only if one returns exactly `0`.
  - `def violation_set(c: Constraint, var: Symbol, D: Set) -> Set` — `solveset` of the violated condition, intersected with D.
  - `def removable_at(s: Expr, e: Expr, var: Symbol, h: Rational) -> bool` — both one-sided limits of s at h exist, are finite and equal `e.subs(var, h)`.
  - `@dataclass(frozen=True) class Gap: interval: sympy.Interval` — a violated subinterval where E is defined.
  - `def equivalent(s: Translated, e: Translated, domain: Domain, strict: bool, var: Symbol, budget: Budget) -> Verdict | Gap | None`
    - `Verdict` from spec 04 steps 1–2; `Gap` when the student's expression is undefined on a subinterval of D (task 5 certifies a point there); `None` when equality is not proven (task 5 refutes).

- [x] **Step 1: Write the failing tests.** Each test's docstring names the spec 04 row it pins.

```python
def eq(student, expected, domain=REALS, strict=False): ...  # translate both from MathJSON trees, then equivalent(...)
def test_removable_hole_default(): assert eq(RATIONAL_FN, X_PLUS_1) == Verdict("correct", "proven", "symbolic")
def test_removable_hole_strict(): assert eq(RATIONAL_FN, X_PLUS_1, strict=True).reason == "undefined_on_domain"
def test_sin2_plus_cos2_is_one(): assert eq(SIN2_PLUS_COS2, ONE).reason == "proven"
def test_log_branch_on_positive_reals(): assert eq(LN_X2, TWO_LN_X, domain=POSITIVE).status == "correct"
def test_sqrt_x2_not_proven_equal_to_x(): assert eq(SQRT_X2, X) is None
def test_sqrt_x_squared_is_gap_on_reals(): assert isinstance(eq(SQRT_X_SQUARED, X), Gap)   # undefined on (−∞, 0)
def test_excluded_point_ignored(): ...   # domain ℝ \ {1}, strict: (x²−1)/(x−1) vs x+1 → correct
def test_removable_at(): assert removable_at((x**2 - 1)/(x - 1), x + 1, x, 1)
def test_pole_not_removable(): assert not removable_at(x + 1/(x - 1), x, x, 1)   # infinite limit
def test_conditionset_is_domain_unproven(): ...   # constraint whose solveset is a ConditionSet → unable_to_verify, domain_unproven
def test_spent_budget_returns_none(): assert prove_equal(x, x, Budget(time.monotonic() - 1)) is False
```

- [x] **Step 2:** Run `uv run pytest tests/unit/verify/test_equivalence.py -q`. Expected: FAIL (module missing).
- [x] **Step 3: Implement** spec 04 steps 1–2.
  - Domain check runs only after `prove_equal` succeeds. For each student constraint, `violation_set`:
    - empty → fine;
    - `FiniteSet` → for each point h in D where E's own constraints hold exactly: `strict` → `incorrect, undefined_on_domain`; otherwise `removable_at` must hold, else `incorrect, pole_on_domain`;
    - an `Interval` or `Union` containing an interval on which E is defined → return `Gap(<first such interval>)`;
    - `ConditionSet`, any other set, or an exception → `unable_to_verify, domain_unproven`.
  - All constraints pass → `correct, proven, symbolic`.
  - Before each SymPy call check `budget.remaining() > 0`; when spent, return `None` (or `domain_unproven` inside the domain step). The pool enforces the hard deadline; this only stops early.
- [x] **Step 4:** Run `uv run pytest tests/unit/verify -q && uv run mypy src`. Expected: PASS.
- [x] **Step 5: Commit** `feat: symbolic equivalence with domain and removable-hole checks`.
