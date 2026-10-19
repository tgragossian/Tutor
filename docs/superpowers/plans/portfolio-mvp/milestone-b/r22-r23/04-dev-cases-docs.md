# Task 4: Dev cases, recapture, rulings and docs

[R22/R23 plan](README.md) · [Spec: dev cases](../../../../specs/2026-10-19-function-input-and-domain-rewrite-design.md#dev-cases) · [Task 9](../tasks/09-dev-cases.md)

**Files:**
- Modify: `evals/verifier/human/dev.src.yaml`, `dev.jsonl` (generated), `REVIEW.md` and its parts
- Create: `docs/decisions/0003-function-parentheses.md`
- Modify: `docs/decisions/README.md`, `../02-execution-rulings.md`, `../tasks/14-pages-ui.md`,
  `../03-execution-status.md`, `../05-follow-ups.md`, `../README.md`, `evals/verifier/README.md`,
  `handoff.md`, spec status line

**Interfaces:**
- Consumes: tasks 1–3 merged; `npm run capture:eval --prefix tools`; `evaluate --draft`.

- [ ] **Step 1: Prove capture assumptions.** Add a temporary entry (not committed) and
  capture `\cos(x)(x+\cos(x))`, `\sin^2(x)`, `\log_2(8)`, `\sec(x^2)`, `\ln\lvert x\rvert`.
  Expected raw MathJSON: a product with `Cos` applied to `x` alone; `Power(Sin(x), 2)`;
  `Log(8, 2)`; `Sec(Power(x, 2))`; `Ln(Abs(x))`. **If any differs, stop and report to Thomas**:
  the spec assumes these parses.
- [ ] **Step 2: Rewrite the 26 cases** listed by the bare-function scan (rerun it; same count
  expected) to parenthesized LaTeX with unchanged label and meaning. Update each rationale's
  wording only where it quotes the old input. Keep `reviewer: 'pending'`.
- [ ] **Step 3: Add regression cases** `d-r22-01..04`, category `unsupported`, label
  `unsupported`, family `inline-r22`, inline spec `{kind: expression, latex: '\sin(x)'}` (or the
  matching function): inputs `\sin x`, `\cos x(x+1)`, `\cos^2x`, `\log_2 8`; rationale
  "R22: function input must be parenthesized."
- [ ] **Step 4:** recapture; `uv run python -m mathtutor.verify.evaluate --set dev --gate B --draft`.
  Expected: 135 cases, FA 0, every R22 case agrees, disagreements 3–6, 8, 9 now agree.
  Record the actual numbers; do not overwrite `results/dev-draft.json`.
- [ ] **Step 5: Docs.**
  - Decision 0003 (≤100 lines): R22 rule, accepted openers, copy, and "amends 0002: LaTeX is
    also read for this reject-only rule". Link it from the decisions index.
  - Rulings file: add R22 and R23 (one bullet each, linking the spec); note R23 amends R18.
  - Task 14 page: MathLive inline shortcuts insert `\fn\left(\placeholder{}\right)` for the
    listed commands; keyboard buttons insert the same. Correct the spec's "task 13" to task 14.
  - Review sheet: new numbers, `d-181-05` resolution (Thomas chose R22 option A), remaining
    disagreements. Execution status, follow-ups, evals README, handoff: link this plan and
    state results. Spec status line: "approved by Thomas, 2026-10-19; implemented in <sha>".
- [ ] **Step 6:** full checks pass; commit
  `test: recapture dev cases under R22; record R22/R23 rulings and draft results`; push.
