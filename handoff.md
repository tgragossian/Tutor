# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22 after Codex's whole-branch review.
Reviewed `main` / `milestone-b` at identical commit 15169a2. Review/docs changes are in the
main checkout; implementation worktree: `.claude/worktrees/milestone-b`. Host recorded at 9bf6b29.

**Milestone B status:** tasks 1–16 implemented and deployed; review complete, **five findings
open (one P1, four P2)**. Fix before closing B, then complete the hours log.
Host sizing stays deferred to milestone C under Thomas's recorded exception.

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

1. **Fix the [2026-10-22 review findings](docs/reviews/2026-10-22-milestone-b/README.md).**
   B-R5 (P1): busy orphan replay deletes live work; reused row IDs can attach a result to
   another user's submission. Fix recovery ownership/identity first, together with B-R2
   (original revision lost during recovery; amend ruling A14). Use a new forward migration.
   B-R1: edited answer resends old payload after retries; B-R3: answer time includes grading;
   B-R4: load checker accepts database failures and wrapper discards failure status.
   Probes, exact owners and regression requirements are split by debugging area in the review.
2. **Host sizing: deferred by Thomas (2026-10-22).** Stay on 1 GB, pool 1 worker / 384 MB, as a
   recorded exception: the worst-case rule (≈973 MiB > 85% of 1 GB) fails, but measured use
   leaves ≥ 281 MiB free under the burst ([host sizing](docs/ops/host-sizing.md)). Revisit in
   milestone C once retrieval's memory is known (local embeddings/index vs API). A fine-tuned
   model will not run on this host at any size; plan it on a provider or separate GPU box.
   Not a blocker for closing milestone B.
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
  separates recorded browser/CI evidence from [fresh local validation](docs/reviews/2026-10-22-milestone-b/04-validation.md).
- Fresh: 890 Python passed / 1 Linux-only skip, 19 Node passed, lint/format/types and 22-problem
  content check passed; dev 136/136 and generated 94/94 agreement, FA 0. Five review probes fail.
  Prior B-A1–B-A5 regression tests pass. No fresh browser, Docker or production run.
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
