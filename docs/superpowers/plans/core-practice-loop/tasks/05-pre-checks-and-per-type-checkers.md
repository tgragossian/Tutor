[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 320–372. Review findings remain unresolved.

### Task 5: Pre-checks and per-type checkers

**Files:**
- Create: `src/mathtutor/verify/checkers.py`, `tests/verify/test_checkers.py`

**Interfaces:**
- Consumes: `translate`, `parse_expected`, `compare`.
- Produces: `def check(spec: AnswerSpec, mathjson: Any, latex: str) -> Verdict | FormatIssue`. It runs in process; Task 7 wraps it in the sandbox.
  - **Pre-checks run first, on `latex`:**
    - empty → `FormatIssue("empty")`
    - `Rejected("incomplete")` → `FormatIssue("incomplete")`
    - a bare decimal matching `^-?\d+\.(\d+)$` with fewer than `decimals` places → `too_few_decimals`
    - a decimal when `decimals is None` → `exact_required`

    Decimal places are counted from the LaTeX, because MathJSON may drop trailing zeros.
  - Any other `Rejected` → `Verdict("unable_to_verify", reason, "none", ms)`.
  - Then the §4.2 table for every type except `implicit_derivative`, which delegates to Task 6.
  - Rounding reasons: `rounding_match` / `rounding_mismatch` (method `rounding`).
  - `multiple_choice` uses `mathjson` as the choice id string, method `exact`.

- [ ] **Step 1: Write the failing tests** (spec values):

```python
NUM = AnswerSpec("numeric", "pi/4")
def test_decimal_rounds_3(): assert check(NUM, mj("dec_0785"), latex("dec_0785")).status == "correct"
def test_decimal_too_few_places(): assert check(NUM, mj("dec_079"), latex("dec_079")) == FormatIssue("too_few_decimals", ANY)
def test_decimal_trailing_zero_counts(): assert check(AnswerSpec("numeric", "0.78"), mj("dec_0780"), latex("dec_0780")).status == "correct"
def test_decimals_2_accepts_079(): assert check(AnswerSpec("numeric", "pi/4", decimals=2), mj("dec_079"), latex("dec_079")).status == "correct"
def test_exact_required(): assert isinstance(check(AnswerSpec("numeric", "pi/4", decimals=None), mj("dec_0785"), latex("dec_0785")), FormatIssue)
def test_exact_form(): assert check(NUM, mj("frac_pi_4"), latex("frac_pi_4")).method == "symbolic"
def test_expression_wrong_sign():
    s = AnswerSpec("expression", "2*x*sin(x) + x**2*cos(x)")
    assert check(s, mj("d_x2sinx_wrong_sign"), latex("d_x2sinx_wrong_sign")).status == "incorrect"
def test_antiderivative_any_constant():
    s = AnswerSpec("antiderivative", "x**3/3")
    for k in ("antideriv", "antideriv_c", "antideriv_5"): assert check(s, mj(k), latex(k)).status == "correct"
def test_antiderivative_ln_abs(): ...      # spec answer "log(x)", student ln|x| → correct on domain (0.1, 5) and on (-5, 5)
def test_limit_tokens(): ...               # oo vs mj("inf") correct; oo vs mj("neg_inf") incorrect; DNE vs mj("dne") correct; DNE vs mj("num_3") incorrect
def test_point_set_order_free(): assert check(AnswerSpec("point_set", ("1", "-1")), mj("set_pts"), latex("set_pts")).status == "correct"
def test_point_set_size_mismatch(): ...    # expected ("1",) → incorrect
def test_multiple_choice(): assert check(AnswerSpec("multiple_choice", "b", choice_ids=("a","b","c")), "b", "").status == "correct"
def test_empty(): assert check(NUM, mj("empty"), "") == FormatIssue("empty", ANY)
def test_incomplete_is_format_issue(): assert isinstance(check(NUM, mj("incomplete"), latex("incomplete")), FormatIssue)  # Review Focus 2
def test_unsupported_is_unable(): assert check(NUM, mj("matrix"), latex("matrix")).status == "unable_to_verify"
```

- [ ] **Step 2:** Run `uv run pytest tests/verify/test_checkers.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement `check`.** The type dispatch is a dict of private functions. `latency_ms` is measured around the whole call.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(verify): pre-checks and answer-type checkers`.

---

<!-- End preserved source. -->
