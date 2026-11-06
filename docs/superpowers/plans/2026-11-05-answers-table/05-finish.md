# Task 5: Finish

[Plan](README.md) · Spec D12

**Files:**
- Modify: `README.md` ("How a hint is made" ladder paragraph; "Evaluation" note)
- Modify: `handoff.md` ("Resume here"), `docs/superpowers/plans/README.md`
- Modify: `docs/ops/runbook-c1.md` (deploy note for 0006/0007)

- [ ] **Step 1: README.** Change the ladder sentence to: "after one, a fast model labels the
  mistake (algebra slip, wrong rule, rule misapplied, incomplete), and each repeat of the same
  type makes the next hint more direct." Add under the Evaluation table: "These results were
  measured with three tries and a ladder that climbed per hint given; the current code allows
  five tries and climbs per mistake made." Move the "In progress" paragraph under "What's
  next" into "How a hint is made" in present tense (keep the one-hint-per-attempt rationale),
  noting that it is on `main` and not yet live.
- [ ] **Step 2: Handoff.** Add a "Resume here" item: answers table on `main`, not deployed;
  deploy only after a fresh backup in `/srv/backups/` and Codex review; migrations 0006 and
  0007 run in the one-shot `migrate` service. Update the `README.md#acknowledgments` link in
  "Working rules" to `README.md#how-this-was-built`.
- [ ] **Step 3: Runbook.** Add the deploy order: back up the DB, `git pull`, build, run
  `migrate` (must exit 0), start `app`, check `/readyz`, submit one wrong answer and confirm
  its row has `attempt_no` 1 and, within a minute, a `mistake_type`.
- [ ] **Step 4: Full CI locally:** the Global Constraints check, then
  `uv run python -m mathtutor.verify.content_check`,
  `uv run python -m mathtutor.verify.evaluate --set dev --gate B`,
  `uv run python tools/check_docs.py`, `npm test --prefix tools`. Expected: all pass;
  verifier gate B unchanged (FA 0/50, FR 0/49).
- [ ] **Step 5: Commit** `docs: answers table, mistake ladder and deploy notes`.
- [ ] **Step 6: Finish the branch** with superpowers:finishing-a-development-branch: merge
  `answers-table` into `main` and push. Do not deploy.
