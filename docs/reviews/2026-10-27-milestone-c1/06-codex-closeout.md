# C1 review: Codex close-out checklist (Markdown updates)

[Review index](README.md) · [Dispositions](05-dispositions.md) · [Handoff](../../../handoff.md)

Written by Claude for Codex, 2026-10-27. Claude has fixed C1-R1..R9 on `milestone-c1`
(`38c2de4`..`9bde1d9`, docs `7535b1d`); Codex owns the verdicts and the Markdown below.
Claude does not mark anything closed. Keep every file at most 100 lines.

## A. Verify (no key, no paid call, no real holdout)

```powershell
.venv\Scripts\python.exe -m pytest -q
npm test --prefix tools
.venv\Scripts\python.exe -m ruff check . ; .venv\Scripts\python.exe -m mypy src
.venv\Scripts\python.exe -m pytest docs/reviews/2026-10-27-milestone-c1/test_review_probes.py -q --runxfail --tb=short
.venv\Scripts\python.exe tools/check_docs.py
```

Claude's run at `7535b1d`: pytest 1611 passed / 3 skipped; Node 48 passed; ruff, mypy,
`content_check` (22 OK) and docs check pass. Expected probe results after the fixes: R3–R8
probes pass; R1's models the old Dockerfile and fails; R2's and R9's assert the designs
Claude replaced (D1, D4) and fail. Judge D1–D4 on the regression tests in dispositions.

## B. Markdown to update, in this order

1. `README.md` (this folder): add a Status column to the findings table (`closed` /
   `reopened: reason`); replace the "Update 2026-10-27" paragraph with the outcome.
2. `05-dispositions.md`: per row, record the verdict and any extra evidence; accept or reject
   D1–D4. A reopened row names the missing test or behavior.
3. `04-validation-and-next-steps.md`: add the rerun results as fresh evidence (date, HEAD);
   mark the fix-order steps done or not.
4. `test_review_probes.py` / `review_ui_probe.mjs`: retire probes now covered by tests in
   `tests/` (point to them), or rewrite R1/R2/R9 to the accepted designs. No strict xfail
   may stay on a fixed finding.
5. `../README.md` (reviews index): one-line outcome for this review.
6. `docs/superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md`: replace Codex's
   "nine findings open" paragraph; confirm or amend R31–R34.
7. `.../c1/20-status.md`: the "Code review fixes" gate row and the intro paragraph.
8. `docs/ops/runbook-c1.md` (top line) and `evals/help/README.md`: remove "waits for Codex"
   wording if all P1 rows close; otherwise name the open rows.
9. `handoff.md` "Resume here" item 1: the result and the next owner step.

## C. Then review the C2 plan (branch `milestone-c2`)

`docs/superpowers/plans/portfolio-mvp/milestone-c/c2/` was rebased onto these fixes and
revised for them ("C1 fixes this plan builds on" in its README). Check it against the
[C spec](../../superpowers/specs/2026-10-26-milestone-c/README.md) and the fixed C1 code;
write findings to a new dated review folder. Thomas still has to answer Q1–Q8 there.
