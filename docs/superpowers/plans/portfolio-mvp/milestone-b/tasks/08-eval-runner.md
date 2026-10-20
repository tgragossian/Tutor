# Task 8: Evaluation runner, metrics and CI gate

[Milestone B plan](../README.md) · [Spec 08](../../../../specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

**Status (2026-10-19):** Complete: 55744b8, 4138181; R10/R11 and no-crash/full-generated-agreement gates apply; a115846 adds partial-input agreement.
See [rulings](../02-execution-rulings.md) and [execution status](../03-execution-status.md); checked steps include recorded replacements.

Actual `Metrics` also includes `unsupported_accept`, `agreement` and `internal_errors`.
`evaluate(..., grade=None)` permits injection; the CLI always supplies `pool.submit`.

**Files:**
- Create: `src/mathtutor/verify/evaluate.py`, `src/mathtutor/verify/mutate.py`
- Create: `evals/verifier/README.md`, `evals/verifier/generated/mutations.jsonl` (generated), `evals/verifier/results/.gitkeep`
- Create: `tests/unit/verify/test_evaluate.py`, `tests/fixtures/evals/tiny.jsonl`
- Modify: `.github/workflows/ci.yml`, `docs/README.md` (link `evals/verifier/README.md`)

**Interfaces:**
- Consumes: `check` (task 5), `load_bundle` (task 1), `loads_exact` for reading every JSONL line.
- Produces:
  - Case record (spec 08): `{id, family, problem_id | inline_spec, answer, label, rationale, reviewer}`; `label ∈ correct | incorrect | unsupported`.
  - `def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]`
  - `@dataclass class Metrics: fa: tuple[int, int]; fr: tuple[int, int]; coverage: tuple[int, int]; abstain: dict[str, tuple[int, int]]; by_kind_reason_method: dict[str, int]`
  - `def evaluate(cases: list[Case], content: LoadedContent) -> tuple[Metrics, list[CaseResult]]`
  - `GATES_B = {"min_cases": 80, "fa_max": 0, "fr_max": 0.02, "coverage_min": 0.85, "generated_fa_max": 0}`
  - CLI: `python -m mathtutor.verify.evaluate --set dev|generated [--gate B] [--out results/<name>.json]`; exits 1 when a gate fails, printing which.
  - `python -m mathtutor.verify.mutate` writes `generated/mutations.jsonl` from the seed problems (deterministic).

- [x] **Step 1: Write the failing tests.**

```python
def test_wilson_zero_of_n(): lo, hi = wilson(0, 100); assert lo == 0 and 0.03 < hi < 0.04
def test_metrics_denominators(): m, _ = evaluate(load_cases(TINY), REAL); assert m.fa == (0, 3) and m.coverage == (2, 3)
def test_unsupported_label_counts_only_in_abstain(): ...   # an "unsupported" case answered FormatIssue counts as agreement
def test_gate_fails_on_false_accept(): ...                  # tiny set with a wrong case labelled incorrect but graded correct → gate exit 1
def test_gate_fails_when_everything_abstains(): ...         # check monkeypatched to unable_to_verify → coverage gate fails
def test_gate_fails_under_80_cases(): ...
def test_report_formats_zero_as_upper_bound(): assert "0 of 120 (95% upper bound" in render_summary(m)
def test_mutations_deterministic(): assert mutate(REAL) == mutate(REAL)
```

- [x] **Step 2:** Run `uv run pytest tests/unit/verify/test_evaluate.py -q`. Expected: FAIL.
- [x] **Step 3: Implement.**
  - A case's verdict agrees with its label when: `correct` ↔ `Verdict.correct`; `incorrect` ↔ `Verdict.incorrect`; `unsupported` ↔ a `FormatIssue` (`unsupported_notation`, `input_too_large`, `empty` or `incomplete`). Abstentions are tallied per label, never counted as agreement for `correct`/`incorrect`.
  - FA = incorrect-labelled cases graded `correct` ÷ incorrect-labelled cases; FR = correct-labelled graded `incorrect` ÷ correct-labelled; coverage = correct-labelled graded `correct` ÷ correct-labelled.
  - `mutate`: for each seed expression problem, emit cases built as **MathJSON trees directly** (labelled `incorrect`): sign flip of one term, dropped inner derivative factor, coefficient off by one, exponent off by one; and `correct` cases from rewrites proven by construction (`a+b` → `b+a`, `2·u` → `u+u`). Each case's `family` is its problem id. The README says these are regression-only and never cited as accuracy (spec 08).
  - Results JSON includes the verifier version, the set's SHA-256, the metrics with Wilson intervals, and per-case outcomes.
- [x] **Step 4: CI.** Python job adds:
  - `uv run python -m mathtutor.verify.evaluate --set generated --gate B`
  - `uv run python -m mathtutor.verify.evaluate --set dev --gate B` — **added in task 9** after human review and passing gates, not merely file creation.
- [x] **Step 5:** Run `uv run python -m mathtutor.verify.mutate && uv run python -m mathtutor.verify.evaluate --set generated --gate B`. Expected: exit 0, FA "0 of N".
- [x] **Step 6: Commit** `feat: verifier evaluation runner, Wilson metrics, generated regression set`.
