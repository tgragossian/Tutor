# Task 3: R22 authored content

[R22/R23 plan](README.md) · [Spec R22 item 5](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#r22-function-input-always-uses-parentheses)

**Files:**
- Modify: `src/mathtutor/verify/content_check.py` (`_self_checks`, `_choice_checks`, `_misconception_checks`)
- Modify: `content/problems/*.yaml` (answer, choice and misconception LaTeX only), then
  regenerate `content/compiled/problems.json` with `npm run compile --prefix tools`
- Test: `tests/unit/verify/test_content_check.py`

**Interfaces:**
- Consumes: `unparenthesized_function`, `FUNCTION_PARENS_DETAIL` (task 2).
- Produces: content-check error lines `"<id>: answer.latex: function input needs parentheses (\\sin)"`,
  same shape for `answer.choices[i].latex` and `misconceptions[i]`.

`statement` text is quoted from OpenStax and is **not** checked or edited.

- [ ] **Step 1: Write failing tests** in `test_content_check.py` (build a problem from a seed
  with `model_copy`):
  - `test_bare_function_in_answer_latex_is_an_error`: answer latex `(1-\sin x)^2` → an error
    naming `answer.latex` and `\sin`.
  - `test_bare_function_in_choice_is_an_error`.
  - `test_bare_function_in_misconception_is_an_error`: the misconception is reported as an
    error, **not** silently skipped as a format issue (Review Focus 1).
  - `test_rejected_misconception_is_an_error`: any misconception whose `check` outcome is a
    `FormatIssue` is an error ("misconception is not gradable: <code>").
  - `test_statement_is_not_checked`: a statement with `\cos x` produces no error.
- [ ] **Step 2:** run them → fail.
- [ ] **Step 3: Implement** the three checks and the gradable-misconception rule.
- [ ] **Step 4:** tests pass; `uv run python -m mathtutor.verify.content_check` now lists the
  seed problems' bare functions.
- [ ] **Step 5: Edit the seed YAML.** Parenthesize every function argument in `answer.latex`,
  choice `latex` and misconception heads (e.g. `(1-\sin(x))^2-(x+\cos(x))\cos(x)`). Keep every
  `review` block unchanged except append to `notes`:
  `2026-10-19: LaTeX parenthesized for R22; meaning unchanged (proved equal to the previous compiled answer).`
- [ ] **Step 6: Prove meaning unchanged.** Before regenerating, save the old compiled file to the
  job tmp directory; after `npm run compile --prefix tools`, a throwaway script asserts for each
  problem that `prove_equal(translate(new).expr, translate(old).expr, budget)` holds for the
  answer and each misconception, and that choice trees prove equal pairwise. Paste the output
  in the commit body; do not commit the script.
- [ ] **Step 7:** content check exits 0; full checks pass; commit
  `feat: authored content LaTeX uses function parentheses (R22)`.
