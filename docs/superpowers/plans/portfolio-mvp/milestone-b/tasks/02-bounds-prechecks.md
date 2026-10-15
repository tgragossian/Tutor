# Task 2: Verify types, structural bounds, pre-checks

[Milestone B plan](../README.md) · [Spec 02](../../../../specs/2026-10-13-portfolio-core/02-answer-contracts.md) · [Spec 03](../../../../specs/2026-10-13-portfolio-core/03-input-bounds.md)

**Files:**
- Create: `src/mathtutor/verify/__init__.py`, `types.py`, `structure.py`, `precheck.py`
- Create: `tests/unit/verify/test_structure.py`, `test_precheck.py`, `test_verify_imports.py`
- Modify: `src/mathtutor/domain.py`

**Interfaces:**
- Consumes: `loads_exact` (task 1); `Answer` union and `Decimals` from `content/schema.py`; `tests/support/mathjson.py` `mj(key)`, `latex(key)`.
- Produces (`domain.py`):
  - `class VerdictReason(StrEnum)`: `proven, rounded_match, choice_match, counterexample, student_undefined, undefined_on_domain, pole_on_domain, rounded_mismatch, choice_mismatch, not_proven, domain_unproven, timeout, internal_error`
  - `class Method(StrEnum)`: `symbolic, domain, refutation, rounding, exact, none`
- Produces (`verify/types.py`, frozen dataclasses, no SymPy import):
  - `SubmittedAnswer(kind: AnswerKind, mathjson: JsonValue | None, latex: str, choice_id: str | None)`
  - `Verdict(status: VerdictStatus, reason: VerdictReason, method: Method)`
  - `FormatIssue(code: FormatIssueCode, detail: str = "")`
  - `CheckRequest(answer_spec: Answer, answer: SubmittedAnswer, request_id: str = "")`
  - `CheckResult(outcome: Verdict | FormatIssue, verifier_version: str, worker_ms: int = 0, queue_ms: int = 0)`
  - `class VerifierBusy(Exception)`
- Produces (`structure.py`): `def check_structure(tree: JsonValue) -> FormatIssue | None` — nodes ≤ 200, depth ≤ 30, integer ≤ 30 digits, `{"num": s}` ≤ 30 significant digits with |exponent| ≤ 30 → else `input_too_large`; a `num` string that is not a decimal literal → `unsupported_notation`.
- Produces (`precheck.py`): `def precheck(answer: SubmittedAnswer, spec: Answer) -> FormatIssue | None`

- [ ] **Step 1: Write the failing tests.**

```python
@pytest.mark.parametrize("key", ["x_plain", "six_x_cos", "rational_fn", "huge_pow"])
def test_captured_shapes_pass_structure(key): assert check_structure(mj(key)) is None     # huge_pow is a cost issue (task 3)
def test_long_int_too_large(): assert check_structure(mj("long_int")).code == "input_too_large"
def test_201_nodes_too_large(): assert check_structure(["Add", *["x"] * 200]).code == "input_too_large"
def test_200_nodes_ok(): assert check_structure(["Add", *["x"] * 199]) is None
def test_depth_31_too_large(): ...   # nested ["Negate", ...] 31 deep; 30 deep passes
def test_num_31_sig_digits(): assert check_structure({"num": "1." + "2" * 30}).code == "input_too_large"
def test_num_exponent_31(): assert check_structure({"num": "1e31"}).code == "input_too_large"
def test_empty_is_empty(): assert precheck(expr_answer(mj("empty"), latex("empty")), EXPR).code == "empty"
def test_placeholder_latex_incomplete(): ...    # mj("incomplete") is "x" but latex has \placeholder → incomplete
def test_empty_group_incomplete(): ...           # typed_pow_empty: latex "x^{}" → incomplete
def test_error_node_incomplete(): ...            # typed_frac_empty → incomplete
def test_decimal_when_exact_required(): ...      # NUMERIC with precision "exact", mathjson {"num": "0.5"} → exact_required
def test_choice_skips_expression_prechecks(): assert precheck(SubmittedAnswer("choice", None, "", "b"), CHOICE) is None
def test_kind_mismatch_raises(): ...             # expression answer for a choice spec → ValueError (web maps to 422)
def test_verify_imports(): ...   # subprocess: import mathtutor.verify.*; assert no mathtutor.web/store/application
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/verify -q`. Expected: FAIL (module missing).
- [ ] **Step 3: Implement** the types, then `check_structure` as one iterative walk (explicit stack, so a deep tree cannot hit Python's recursion limit), then `precheck`.
  - `exact_required` applies only when the top-level tree of a `numeric` answer with `precision: exact` is a `{"num": ...}` literal (spec 02: a decimal elsewhere is graded as an exact rational).
  - The `incomplete` LaTeX check is a string test: `"\\placeholder" in latex or re.search(r"\{\s*\}", latex)`, excluding `\{\}` (escaped braces).
- [ ] **Step 4:** Run `uv run pytest -q && uv run mypy src`. Expected: PASS. Add `mathtutor.verify` to the mypy `strict` override.
- [ ] **Step 5: Commit** `feat: verifier types, structural bounds and pre-checks`.
