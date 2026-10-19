# Task 2: R22 pre-check rule

[R22/R23 plan](README.md) · [Spec R22](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#r22-function-input-always-uses-parentheses)

**Files:**
- Create: `src/mathtutor/verify/latex_rules.py`
- Modify: `src/mathtutor/verify/precheck.py` (`precheck`, after the `incomplete` check)
- Test: `tests/unit/verify/test_latex_rules.py`, `tests/unit/verify/test_precheck.py`

**Interfaces:**
- Produces: `unparenthesized_function(latex: str) -> str | None` returns the first offending
  command (e.g. `"\\sin"`) or None; `FUNCTION_PARENS_DETAIL: str` (the README copy, verbatim).
  Task 3 imports both.
- `precheck` returns `FormatIssue(FormatIssueCode.UNSUPPORTED_NOTATION, FUNCTION_PARENS_DETAIL)`
  when `unparenthesized_function(answer.latex)` is not None. Choice answers are never checked.

Scan approach (a small hand scanner, not one regex): find `\name` where name is a listed
command and the next character is not a letter; skip any run of `^`/`_` followed by a braced
group or one token; skip whitespace and `\,` `\;` `\!` `\ `; then require an accepted opener
from the README. Escaped `\\` is not a command start.

- [ ] **Step 1: Write failing tests** in `test_latex_rules.py`:
  - `test_rejects` parametrized → offending command returned:
    `\sin x`, `\cos x(x+1)`, `\cos^2x`, `\ln 2`, `\log_2 8`, `(1-\sin x)^2`,
    `\tan\frac{x}{3}`, `\exp x`, `\sin(x)+\cos x` (→ `\cos`).
  - `test_accepts` parametrized → None:
    `\sin(x)`, `\sin\left(x\right)`, `\sin^2(x)`, `\sin^{2}\left(x\right)`, `\log_2(8)`,
    `\log_{10}(x)`, `\ln\lvert x\rvert`, `\ln\left|x\right|`, `\ln|x|`, `\sin (x)`,
    `\sin\,(x)`, `\sinh x`, `\lnot`, `\left(x\right)`, `x^2+1`, `e^{x}`, empty string.
  - `test_detail_copy`: `FUNCTION_PARENS_DETAIL == "Put the function's input in parentheses, like sin(x)."`
- [ ] **Step 2:** `uv run pytest tests/unit/verify/test_latex_rules.py -q` → fails (import error).
- [ ] **Step 3: Implement** `unparenthesized_function` and the constant in `latex_rules.py`.
- [ ] **Step 4:** test file passes.
- [ ] **Step 5: Failing tests** in `test_precheck.py`:
  - `test_bare_function_is_unsupported_notation`: expression answer, latex `\sin x`, valid
    mathjson `["Sin","x"]` → `FormatIssue(UNSUPPORTED_NOTATION, FUNCTION_PARENS_DETAIL)`.
  - `test_parenthesized_function_proceeds`: latex `\sin(x)` → None.
  - `test_incomplete_wins_over_parens`: latex `\sin\placeholder{}` → `INCOMPLETE`.
- [ ] **Step 6:** wire it into `precheck`; tests pass.
- [ ] **Step 7:** run the full suite. Any existing test that submits bare-function LaTeX through
  `check`/`precheck` and expects grading gets its LaTeX parenthesized (math unchanged); list
  each such test in the commit body. Do not weaken the rule to make a test pass.
- [ ] **Step 8:** full checks pass; commit `feat: require parentheses on function input (R22)`.
