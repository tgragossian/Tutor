# Task 9: 80 human-reviewed dev cases

[Milestone B plan](../README.md) · [Spec 08](../../../../specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

**Status (2026-10-20): complete.** All 136 cases are reviewed and recaptured (`tg`):
49 correct, 50 incorrect, 37 unsupported. R24 is implemented; non-draft gate B passes.
[dev-b.json](../../../../../../evals/verifier/results/dev-b.json): FA 0/50 (95% upper bound 7.1%),
FR 0/49, coverage 49/49, unsupported accepts 0/37, agreement 136/136. CI is green;
[release/merge checklist](../r24/02-release.md). Merged to `main` in 102a22f.

**Files:**
- Create: `evals/verifier/human/dev.src.yaml`, `evals/verifier/human/dev.jsonl` (generated), `tools/capture/eval.mjs`
- Modify: `tools/package.json` (script `capture:eval`), `.github/workflows/ci.yml`, `evals/verifier/README.md`

**Interfaces:**
- Consumes: the capture page and Playwright setup from milestone A task 2; `evaluate` CLI (task 8).
- Produces: `dev.jsonl` — one spec 08 case per line, `answer.mathjson` captured from real MathLive, `answer.latex` as typed, plus `raw_latex` (the authored source).

**Authoring format (`dev.src.yaml`, single-quoted LaTeX):**

```yaml
- id: d-111-01
  family: openstax-c1-3.3-111        # a seed problem id, or "inline-<name>" with inline_spec
  problem_id: openstax-c1-3.3-111
  latex: '\frac{39}{(x+1)^2}+270x^4'
  label: correct
  rationale: 'Terms reordered.'
  reviewer: 'pending'                 # Thomas fills "tg" when reviewed
```

**Required coverage (spec 08), at least these counts, 80+ total:**

| Category | Min | Examples |
|---|---:|---|
| Correct but tricky forms | 15 | factored vs expanded, `\sec^2` vs `1/\cos^2`, `x^{-2}` vs `1/x^2` |
| Typical errors | 20 | each seed misconception, sign slips, missing inner derivative |
| Domain traps | 12 | removable hole default/strict, `\ln(x^2)` vs `2\ln x`, `\sqrt{x^2}` vs `x` |
| Near-equal perturbations | 8 | `+0.000000001`, `0.5833` for `-200/343` |
| Partial / placeholder input | 6 | `x^{}`, `\frac{1}{}`, empty |
| Unsupported notation | 8 | matrix, `f(2x)`, `\sin^{-1}`, `\infty`, other variable |
| Resource limits | 5 | `10^{10^{10}}`, 40-digit integer, 201-node sum |
| Decimals at rounding boundaries | 6 | `-0.5830`, `-0.5835`, `-0.58`, exact `-\frac{200}{343}` |

- Inline specs (`inline_spec: {kind, latex, domain, strict_domain, precision}`) cover cases the seeds cannot (e.g. the `(x²−1)/(x−1)` hole). They are compiled by the same compiler call the capture tool already makes.
- `family` assignment rule: every case derived from one source problem shares its family (dev/final split is by family; final is milestone E).

- [x] **Step 1: Write `tools/capture/eval.mjs`.** It reads `dev.src.yaml`, types each `latex` into a real MathLive field in Chromium (same page as milestone A capture), reads `mf.getValue()` and the raw MathJSON with a fresh `ComputeEngine`, and writes `dev.jsonl` sorted by id. Partial-input cases use `keys` (as in `cases.json`) so the placeholder shapes are real.
- [x] **Step 2: Write the 80+ cases** in `dev.src.yaml` with `reviewer: 'pending'`, each with a rationale that states why the label is right (worked check for `correct`, the specific error for `incorrect`).
- [x] **Step 3:** Run `npm run capture:eval --prefix tools`, then `uv run python -m mathtutor.verify.evaluate --set dev --gate B`.
  - Expected: a report. Every disagreement is either a verifier bug (fix it in the owning module with a unit test first) or a labelling question for Thomas. **Never edit a label to make it pass** (spec 08).
- [x] **Step 4: Human gate (Thomas).** All 136 source cases reviewed in 9b2e1f2, including the seven R24 relabels and `d-sqsq-02`'s `[0, inf)` domain. b5ad4b2 recaptures these marks and labels exactly.
- [x] **Step 5:** 8a0bb40 adds `--set dev --gate B` to CI. Reviewed captures are in b5ad4b2; reviewer/category enforcement remains unchanged. CI run 39504828416 passes after d673400 fixes Linux test teardown.
- [x] **Step 6:** Non-draft `evaluate --set dev --gate B --out evals/verifier/results/dev-b.json` passes at b5ad4b2. FA 0/50, FR 0/49, coverage 49/49; all 136 outcomes agree.
- [x] **Step 7: Commit** reviewed captures (b5ad4b2), release evidence (e995438) and CI gate (8a0bb40). Task 9 is done; merge to `main` is Thomas's next action, preserving milestone-b's handoff. No assistant co-author trailers.
