# Task 9: 80 human-reviewed dev cases

[Milestone B plan](../README.md) · [Spec 08](../../../../specs/2026-10-13-portfolio-core/08-verifier-evaluation.md)

**Status (2026-10-20):** steps 1–4 complete; 9b2e1f2 records 136 `tg` source cases:
49 correct, 50 incorrect, 37 unsupported. Captures still have old labels and pending markers.
[R24 implementation and release](../r24/README.md) must precede recapture and steps 5–7.
No reviewed R24 gate result exists; see [review sheet](../../../../../../evals/verifier/human/REVIEW.md).

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
- [x] **Step 4: Human gate (Thomas).** All 136 source cases reviewed in 9b2e1f2, including the seven R24 relabels and `d-sqsq-02`'s `[0, inf)` domain. Preserve `tg` marks; recapture remains pending.
- [ ] **Step 5:** Add `--set dev --gate B` to CI. Require human reviewer `tg` on every dev row; reject `pending`/blank/generated reviewers for release. Regenerate captured JSONL after source review; preserve a separate draft path. Enforcement, category checks and `--draft` landed in bdb1710; source review is complete; the CI step now waits for R24 and recapture.
- [ ] **Step 6:** Run `uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev-b.json`. Expected: exit 0 with FA 0 observed, FR ≤ 2%, coverage ≥ 85%.
- [ ] **Step 7: Commit** reviewed captures and actual gate evidence (body: category counts and metrics). Then merge tasks 1–9 to `main` after required checks. No assistant co-author trailers.
