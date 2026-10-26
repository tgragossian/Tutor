# C1 task 15: load, memory, deploy and documentation

[C1 plan](README.md) · Previous: [evaluation](18-evaluation.md)

### Task 15: Mixed-load evidence, host sizing and release

**Files:** Modify `tools/load/submit_burst.py` (add a help mode using the scripted generator),
`tools/load/measure.sh`, `docs/ops/host-sizing.md`, `docs/ops/runbook.md`, `docs/ops/security.md`,
`deploy/compose.yaml` (secret env `MATHTUTOR_ANTHROPIC_API_KEY` from the host's env file,
`MATHTUTOR_GUARD_POOL_MEMORY_MB`), `handoff.md`, C status pages; Test `tests/unit/test_submit_burst.py` (extend).

**Interfaces:** Consumes the whole C1 stack. Produces evidence only.

- [ ] **Step 1: Failing test:** `test_burst_help_mode_reports_grading_latency` — the burst tool's
  help mode reports grading p95 separately from help p95 and fails if any grading request
  returned `verifier_busy` while only help traffic was saturating.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. **Step 4:** Run → PASS.
- [ ] **Step 5: Local container measurement:** run the production image with the real corpus,
  scripted generator and both pools; 20 concurrent grading + 20 concurrent help requests for
  60 s. Record RSS of web, grading worker, guard worker and Caddy, index build time, and grading
  p95 versus the B baseline in `docs/ops/host-sizing.md`. Apply the headroom rule; if 1 GB fails,
  write the 2 GB move into the runbook (Thomas approved 2 GB on 2026-10-26).
- [ ] **Step 6: Docs:** runbook gains "Set the Anthropic key" (env file on the host, never in git,
  console spend limit and auto-reload off) and "Turn help off" (`MATHTUTOR_HELP_GENERATOR=off`).
  Security page records provider processing of student text, logging exclusions and key handling.
- [ ] **Step 7: Gate check:** all of these must be true, with links in the C1 status page:
  CI green (Python, Node, container e2e); `content_check` and verifier gates unchanged;
  Task 14 holdout gates pass; mixed-load/memory recorded; demo recorded (one cited hint on a
  wrong derivative, one abstention on an out-of-book question).
- [ ] **Step 8 (owner):** Thomas deploys with the runbook, sets the key, checks `/readyz`,
  tries one hint and one abstention on the live site, and reports back.
- [ ] **Step 9:** Update `handoff.md`, the [open register](../03-open-decisions.md) (C-O3 result,
  C-O5 done, C-P1/C-P2 closed with links) and the specs index; commit
  `docs: C1 released` after Thomas confirms.
