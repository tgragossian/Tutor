# C2 task 8: release docs and owner checklist

[C2 plan](README.md) · Previous: [evaluation](13-evaluation.md)

### Task 8: Docs, status page, burst mode

**Files:** Create `docs/superpowers/plans/portfolio-mvp/milestone-c/c2/20-status.md`.
Modify `docs/ops/runbook-c1.md` (one "Questions (C2)" section: switch off with
`question.enabled`, what is logged), `docs/ops/security.md` (question text: never stored or
logged; sent to Anthropic), `tools/load/submit_burst.py` (`--mode help --help-type question`),
`handoff.md`, `docs/superpowers/plans/portfolio-mvp/03-rag.md` (C2 plan link),
`milestone-c/03-open-decisions.md` (Q1–Q8 status). Test: `tests/unit/test_submit_burst.py`.

- [ ] **Step 1: Failing test:** burst tool builds a question body (fixed question text,
  `help_type="question"`) when `--help-type question` is given; default stays `hint`.
- [ ] **Step 2:** Run it → FAIL. Implement → PASS.
- [ ] **Step 3:** Write `20-status.md` (≤ 100 lines), mirroring C1's: done table, owner
  checklist, gate evidence table. Owner checklist, in order:
  1. Approve Q1–Q8 (or change them) and the C2 gates.
  2. Review 34 cases; set `reviewed_by: tg`; approve the rubric addendum.
  3. C1 released first (C2 needs C1's chosen model and live help).
  4. Top up credit if needed (Q8); paid C2 dev run; audit; recompute.
  5. Freeze prompts; one-shot C2 holdout with the remaining-credit cap.
  6. Container smoke (`E2E=1 bash tests/container/smoke.sh`) including the question step.
  7. Deploy; live check: one cited answer to a concept question, one "just tell me the
     answer" redirected or blocked, one off-topic question abstained.
  8. Commit `docs: C2 released`.
- [ ] **Step 4:** Update handoff "Resume here" and the open register; run
  `uv run python tools/check_docs.py`, full `uv run pytest -q`, `npm test --prefix tools`.
- [ ] **Step 5:** Commit `docs(c2): status, runbook, security and handoff`.

## After Task 8

Final whole-branch review (most capable model), then finishing-a-development-branch. Nothing
is deployed, merged or pushed without Thomas.
