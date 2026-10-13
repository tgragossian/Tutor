[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 512–555. Review findings remain unresolved.

### Task 10: Verifier evaluation set and CI gate

**Files:**
- Create:
  - `eval/sympy_to_mathjson.py`: SymPy → MathJSON in the ADR-0001 encoding; used only for evaluation
  - `eval/generate_cases.py`
  - `eval/generated_cases.yaml` (committed output)
  - `eval/verifier_cases.yaml` (hand-written)
  - `eval/run_verifier_eval.py`
  - `tests/eval/test_eval_runner.py`
- Modify: `ci.yml`. Add the step `uv run python eval/run_verifier_eval.py --fail-on-false-accept`.

**Interfaces:**
- **Case format:** `{id, problem: <problem id> | inline AnswerSpec fields, student: {latex, mathjson}, label: correct | incorrect | unsupported, note}`.
- **Generator, per seed problem:**
  - correct variants that are guaranteed equal: `expand`, `factor`, `together`, `trigsimp` rewrites, + constants for antiderivatives
  - incorrect variants that are guaranteed different: negate, ×2, + 1 (non-antiderivative), drop the outermost chain factor, power ± 1

    A variant is kept only if SymPy proves `simplify(variant - expected) != 0` at a rational sample point. This label check is independent of the code under test.
- **Hand-written:** ≥ 80 cases covering every captured fixture key plus classic traps:
  - `sin^2 x` vs `sin(2x)`
  - `log` base confusion
  - `ln|x|`
  - decimal rounding
  - `DNE` vs `∞`
- **Runner:** `run_verifier_eval.py [--fail-on-false-accept] [--out eval/report.md]`. It runs each case through `VerifierPool` and prints a table by `answer_type` × `method` with:
  - FA rate (label incorrect, verdict correct)
  - FR rate (label correct, verdict incorrect)
  - inconclusive rate (label correct or incorrect, verdict unable)
  - `unsupported` handled rate
  - p50/p95 latency

  It exits 1 if FA > 0 under the flag.

- [ ] **Step 1: Write the failing tests:** on a 3-case inline set, `summarize(results)` gives the right counts per bucket; the runner's exit code is 1 when a crafted false accept exists.
- [ ] **Step 2:** Run `uv run pytest tests/eval -v`. Expected: FAIL.
- [ ] **Step 3:** Implement the converter, the generator and the runner. Write the hand-written cases.
- [ ] **Step 4:** Run `uv run python eval/generate_cases.py && uv run python eval/run_verifier_eval.py --fail-on-false-accept`.
  - **Expected:** ≥ 300 total cases; FA = 0; FR ≤ 2%; inconclusive ≤ 5%; p95 < 1 s.
  - **If a threshold is missed, stop and report the failing cases.** Fix the verifier; do not relabel.
- [ ] **Step 5: Commit** `eval: verifier evaluation set, runner, CI gate`. Include `eval/report.md`.

---

<!-- End preserved source. -->
