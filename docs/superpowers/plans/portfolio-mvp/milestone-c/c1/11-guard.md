# C1 task 3: leak guard

[C1 plan](README.md) · [Interfaces](03-interfaces.md) · Previous: [foundation](10-foundation.md) · Next: [corpus](12-corpus.md)

### Task 3: Extraction, classification and the guard pool

**Files:** Create `src/mathtutor/help/leak_guard.py`; Modify `src/mathtutor/web/app.py`
(start/close a second `VerifierPool` as `app.state.guard_pool`); Test
`tests/unit/help/test_leak_guard.py`, `tests/integration/test_guard_pool.py`.

**Interfaces:** Consumes `parse_latex` (Task 2), `Pool.submit(CheckRequest) -> CheckResult`
(`application/practice.py`), `GuardLimits` (Task 1). Produces `LeakGuard`, `LeakStatus`,
`GuardResult`, `extract_candidates`, `classify(result: CheckResult) -> LeakStatus` (03).

Classification of a candidate checked against an `ExpressionAnswer` built from the reference
(numeric: same LaTeX/MathJSON/variable/domain; choice: the correct choice's MathJSON; always
`strict_domain=False`):

| Checker outcome | Status |
|---|---|
| `correct` (any reason) | `LEAK` |
| `incorrect` + `counterexample` | `NO_MATCH` |
| `incorrect` + `student_undefined` / `undefined_on_domain` / `pole_on_domain` | `LEAK` (formula equality before domain) |
| `unable_to_verify`, any `FormatIssue`, `VerifierBusy`, deadline spent | `UNCHECKED` |
| parse rejected | `UNCHECKED` |
| parsed with non-empty `foreign` | `NO_MATCH` (reason `foreign_symbols`, counted separately) |

Extra deterministic rules (no worker call): choice problems block `\b(option|choice|answer)\s*\(?{correct}\)?\b`
and `\({correct}\)` case-insensitively; numeric problems with `precision.decimals` block any
decimal literal with ≥ 2 decimal places in prose or math. Decision: any `LEAK`/`UNCHECKED` → `block`;
`extract_candidates` returning `None` (more than 20) → `block`; zero candidates → `no_detected_math`
(deliverable); otherwise `pass`. Duplicate candidates (same parsed tree JSON) are checked once.

- [ ] **Step 1: Failing unit tests** (a `FakePool` returning scripted `CheckResult`s):
  - `test_extracts_all_delimiters`: `$a$`, `$$b$$`, `\(c\)`, `\[d\]`, a line `y' = e`, and
    `f'(x) = g` yield candidates `a, b, c, d, e, g` with their origins; escaped `\$` is prose.
  - `test_unbalanced_delimiter_blocks`: `"$2x"` → decision `block`, reason `malformed_math`.
  - `test_classify_table`: one assertion per table row above.
  - `test_choice_letter_blocks` / `test_choice_formula_blocks`: correct `a` → "option (a)" blocks;
    "consider (b)" for wrong choice passes; the correct choice's formula in `$…$` blocks.
  - `test_numeric_decimal_blocks`: answer with `decimals: 2`, text "about 0.54" → block.
  - `test_more_than_20_blocks`, `test_deadline_spent_blocks` (clock past deadline → `UNCHECKED`).
  - `test_result_has_no_latex`: `GuardResult` fields contain only counts and a reason code.
- [ ] **Step 2:** `uv run pytest tests/unit/help/test_leak_guard.py -q` → FAIL.
- [ ] **Step 3:** Implement. Each candidate gets `CheckRequest(request_id=f"guard:{n}")` through
  the guard pool; stop at the first `LEAK`/`UNCHECKED` (remaining are irrelevant to the decision).
- [ ] **Step 4: Integration test with the real worker** (`tests/integration/test_guard_pool.py`):
  for problem `adapted-c1-3.5-x2cosx`, `$x(2\cos x - x\sin x)$` → block (leak, via correct choice
  `a`); `$2x\cos x$` (distractor d) → pass; for `openstax-c1-3.6-215`, `$126(7x-4)^2$` and
  `$18\cdot 7(7x-4)^2$` → block, `$18(7x-4)^2$` → pass, `$18u^2$` → pass (foreign `u`). Run `uv run pytest tests/integration/test_guard_pool.py -q` → PASS.
- [ ] **Step 5: Wire the pool.** In `create_app`, start `VerifierPool(size=1, deadline_s=2.0,
  queue_max=4, queue_wait_s=1.0, memory_mb=settings.guard_pool_memory_mb)` only when help is
  enabled (Task 12 decides enabled); `/readyz` ignores the guard pool. Test
  `test_guard_pool_not_started_when_help_off` in `tests/integration/test_app.py`. Run full pytest → PASS.
- [ ] **Step 6:** Commit `feat(help): fail-closed leak guard with its own verifier pool`.
