# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22 end of day. Work continues in the `milestone-b`
worktree (`.claude/worktrees/milestone-b`). `main` and `milestone-b` are identical; the host runs
`main` 9bf6b29.

**Milestone B status:** all tasks 1–16 are implemented and deployed. Not yet closed: the host
memory numbers (step 3 of task 16), a whole-branch review, and the hours log.

## Live site (https://tutor.thomasgragossian.dev)

- Practice loop from `main` 9bf6b29: accounts, practice on three derivative topics with MathLive,
  22 reviewed problems (7 + 7 + 8), history with "Clear history". `/readyz` ready, `servable` 22;
  migrations 0001–0002.
- First `/readyz` after `up -d` returns 502 for 30–60 s while the SymPy worker starts: normal.
- Memory before the 2026-10-22 burst: app+worker 136 MiB, Caddy 15 MiB, 358 MiB available,
  118 MiB in swap.
- Deploy = the [runbook](docs/ops/runbook.md) "Update to the latest `main`" block (Thomas runs
  it in Lightsail browser SSH). `migrate` must show `Exited (0)`. Never `compose down -v`.

## Done 2026-10-22

- Task 15: Thomas reviewed and approved all 16 drafts (3c0141c); deployed. His simplified form
  of 223 was checked equivalent by SymPy and the live verifier. Selection/practice unit tests pin
  the original six problems (`tests/support/content.py`); container smoke skips ahead to 221.
- Task 16 (375ab7c, 9bf6b29): `MATHTUTOR_POOL_SIZE` / `MATHTUTOR_POOL_MEMORY_MB` settings;
  `tools/load/submit_burst.py` (16 users submit dev case `d-181-07` at once) and
  `tools/load/measure.sh` (runs it on the host, reports peak memory and VmHWM); uvicorn
  `--no-access-log` (requests were logged twice; smoke now checks); browser e2e runs against
  the production image in CI (green, run 39828899000); [verifier docs](docs/verifier/README.md);
  [dev-b results](evals/verifier/results/dev-b.md); README status "practice loop live".
- Thomas raised automated problem sets (not just a bank). The plan has the extraction pipeline
  (expansion queue #4); generated problems (templates or LLM) are not planned yet: decide
  with Thomas whether to add them and where.

## Resume here

1. **Whole-branch review of milestone B** (Thomas is asking Codex). Record findings under
   `docs/reviews/` as before; fix before closing the milestone.
2. **Host sizing:** the 2026-10-22 run of `bash tools/load/measure.sh https://tutor.thomasgragossian.dev`
   was cut off during sign-ups (10/min limit) before the peaks printed. Rerun or paste the full
   output, record it in [host sizing](docs/ops/host-sizing.md), apply the 85% rule and keep or
   change the pool settings in `deploy/.env` (or propose the 2 GB bundle).
3. Record actual hours with Thomas ([hours](docs/ops/hours.md)); 30-hour checkpoint pending.
4. [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md): verifier is
   slow on wrong answers to nested trig (`sin(cos 7x)`); `content_check` lacks a hard deadline.
5. Then milestone C (RAG hints). First confirm OpenStax's licence allows RAG ingestion.

## Working notes for Claude

- On this Windows/OneDrive checkout: `UV_LINK_MODE=copy` for `uv add`; Python edit scripts need
  `encoding="utf-8"` and raw strings for LaTeX (backslashes were lost several times today);
  prefer the Edit tool for LaTeX. Playwright must click MathLive with `{delay: 80}`.
- The ledger is `.superpowers/sdd/README/progress.md` (git-ignored); rulings A1–A21 are tracked in
  [06-app-track-rulings](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md).

## Evidence and navigation

- [Documentation tree](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)
  owns task completion and outstanding gates.
- [Verification evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  separates browser/CI evidence from the [review validation](docs/reviews/2026-10-21-milestone-b/03-validation.md).
- [Reviewed verifier result](evals/verifier/results/README.md): FA 0/50 (95% upper bound 7.1%),
  FR 0/49, coverage 49/49, agreement 136/136; no internal errors. This is a dev set.
- [File map](docs/superpowers/plans/portfolio-mvp/milestone-b/01-file-map.md),
  [debugging tree](docs/ops/debugging/README.md), [security](docs/ops/security.md),
  [API contracts](contracts/README.md).
- [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md)
  distinguish release gates from deferred cleanup.

## Working rules

- Every Markdown file stays at most 100 lines, split by responsibility with a parent link.
- Preserve [original references](docs/handoff/README.md) and [dated reviews](docs/reviews/README.md).
- Never relax false-accept or containment gates; describe the verifier as proof-based/SymPy.
- No assistant co-author trailers; assistance is acknowledged in [README](README.md#acknowledgments).
- Actual hours belong in the [hours log](docs/ops/hours.md); do not infer them from agent runtime.
- RAG hints, operations/final evaluation and the [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md)
  follow the deployed practice loop.
