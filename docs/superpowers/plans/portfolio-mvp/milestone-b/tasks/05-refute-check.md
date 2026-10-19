# Task 5: Refutation and the `check` dispatcher

[Milestone B plan](../README.md) · [Spec 02](../../../../specs/2026-10-13-portfolio-core/02-answer-contracts.md) · [Spec 04](../../../../specs/2026-10-13-portfolio-core/04-equivalence.md)

**Status (2026-10-19):** Complete: dbeea51..9d06779; R17/R20/R21 refine witnesses/rounding; B-C1 fixed in 8346d2a.
See [rulings](../02-execution-rulings.md) and [execution status](../03-execution-status.md); checked steps include recorded replacements.

Implementation uses an allowlisted interval-tree walker, replacing the `lambdify` recipe below;
`VERIFIER_VERSION` now lives in `verify/types.py` (task 7).

**Files:**
- Create: `src/mathtutor/verify/refute.py`, `numeric.py`, `check.py`
- Create: `tests/unit/verify/test_refute.py`, `test_numeric.py`, `test_check.py`

**Interfaces:**
- Consumes: tasks 2–4 (`precheck`, `check_structure`, `translate`, `equivalent`, `Gap`, `Budget`, `to_sympy_set`).
- Produces:
  - `def sample_points(domain: Domain, seed: int = 0, n: int = 20) -> list[Rational]` — n rationals from D with a fixed seed, plus finite endpoints and midpoints of each interval, excluding excluded points and open endpoints.
  - `def refute(s: Translated, e: Translated, var: Symbol, points: list[Rational], budget: Budget) -> VerdictReason | None` — `student_undefined` or `counterexample` at the first certified point, else `None`.
  - `def round_matches(expected: Rational, student: Decimal, decimals: int) -> bool` — `ROUND_HALF_EVEN` at N places on both, compared exactly.
  - `VERIFIER_VERSION: str` = `f"{__version__}+{os.environ.get('MATHTUTOR_GIT_SHA', 'dev')}"`
  - `def check(req: CheckRequest, deadline_s: float = 3.0) -> CheckResult`

- [x] **Step 1: Write the failing tests.**

```python
def test_tiny_perturbation_refuted(): assert refute(T("x + 1/1000000000"), T("x"), x, pts(REALS), B) == "counterexample"
def test_ln_x2_vs_2lnx_student_undefined(): assert refute(T("2 ln x"), T("ln(x^2)"), x, pts(NONZERO), B) == "student_undefined"
def test_sqrt_x2_vs_x_counterexample(): assert refute(T("sqrt(x^2)"), T("x"), x, pts(REALS), B) == "counterexample"
def test_equal_functions_not_refuted(): assert refute(T("sin(2x)"), T("2 sin x cos x"), x, pts(REALS), B) is None
def test_overlapping_enclosures_never_refute(): ...  # x + 10**-70 vs x: enclosures overlap at 60 digits → None (abstain)
def test_sample_points_deterministic_and_in_domain(): ...
@pytest.mark.parametrize("expected,student,n,ok", [("2.675", "2.68", 2, True), ("2.665", "2.66", 2, True),  # half-even
    ("200/343", "-0.583", 3, False), ("-200/343", "-0.583", 3, True), ("-200/343", "-0.58", 3, False), ("1/3", "0.333", 3, True)])
def test_round_matches(expected, student, n, ok): assert round_matches(Rational(expected), Decimal(student), n) is ok
def test_check_choice(): assert check(choice_req("b", correct="b")).outcome == Verdict("correct", "choice_match", "exact")
def test_check_numeric_decimal(): ...       # seed 253: {"num": "-0.583"} → correct, rounded_match, rounding
def test_check_numeric_exact_symbolic(): ...  # 253 with exact -200/343 entered as Divide → correct, proven
def test_check_expression_seed_answers(): ...  # every seed problem's own expected MathJSON graded against itself → correct
def test_check_gap_certified(): ...         # sqrt(x)^2 vs x on ℝ → incorrect, undefined_on_domain, method domain
def test_check_unproven_abstains(): ...       # a pair no strategy proves and no point refutes → unable_to_verify, not_proven
def test_check_format_issue_passthrough(): ...  # empty / incomplete / too large / unsupported → FormatIssue outcome
def test_check_never_raises(): ...           # hypothesis over submitted trees against a seed spec
```

- [x] **Step 2:** Run `uv run pytest tests/unit/verify -q`. Expected: the new tests FAIL.
- [x] **Step 3: Implement.**
  - `refute`: `mpmath.iv` with `mp.dps = 60`. At each point, first check student constraints exactly with Rationals (violated where E's enclosure is real and finite → `student_undefined`); otherwise evaluate both enclosures via `lambdify(var, expr, modules=[ivmath])` and return `counterexample` iff they are disjoint. Evaluation errors at a point skip that point.
  - `check` order: (1) kind mismatch → `ValueError`; (2) `choice` → id equality; (3) `check_structure`; (4) `precheck`; (5) numeric with `Decimals` and a top-level `{"num": s}` → `round_matches` against the expected value computed from the expected tree; (6) otherwise translate both, `equivalent`; on `Gap` certify the interval's midpoint with `refute` → `incorrect, undefined_on_domain, domain`, else `domain_unproven`; on `None` refute with `sample_points` → `incorrect` or `unable_to_verify, not_proven`.
  - A `Rejected` from translating the student → `FormatIssue(code)`; from translating the **expected** answer → `unable_to_verify, internal_error` (content bug, logged; task 6 prevents it).
  - Exact numeric answers use the domain `{intervals: [(-inf, inf)]}` (constant expressions).
- [x] **Step 4:** Run `uv run pytest -q && uv run mypy src`. Expected: PASS.
- [x] **Step 5: Commit** `feat: certified refutation, rounding rule and check dispatcher`.
