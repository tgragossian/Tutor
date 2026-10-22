# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22, after Claude fixed Codex's whole-branch review.
`main` and `milestone-b` are identical (Codex's review adbf0e9, fixes ca54407, docs after it).
Implementation worktree: `.claude/worktrees/milestone-b`. The host still runs 9bf6b29.

**Milestone B status:** tasks 1–16 done; review findings B-R1–B-R5 **fixed** (not yet deployed).
To close B: Thomas deploys (migration 0003), then the hours log.
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
- Task 16 (375ab7c, 9bf6b29): pool size/memory settings; `tools/load/submit_burst.py` +
  `measure.sh` (host burst, peak memory); uvicorn `--no-access-log`; browser e2e on the
  production image in CI; [verifier docs](docs/verifier/README.md), [dev-b results](evals/verifier/results/dev-b.md).
- Codex's whole-branch review ([2026-10-22](docs/reviews/2026-10-22-milestone-b/README.md)):
  five findings, all fixed in ca54407; how each was fixed, deviations and tests are in the
  [dispositions](docs/reviews/2026-10-22-milestone-b/06-dispositions.md). In short:
  - **B-R5/B-R2:** migration 0003 (`reserved_revision`, `lease`, `leased_at` on `submissions`).
    Orphan recovery claims an exclusive lease, grades the stored revision (not the retry's),
    only the lease holder deletes, and transaction B checks UUID + presentation before storing.
    A14 amended. Pre-0003 orphans are dropped as stale. Deviation: any holder may finalize (the
    unique result row keeps one). AUTOINCREMENT deferred to follow-ups (needs a table rebuild).
  - **B-R3:** `seconds_on_item` ends at the original submission time, also after recovery.
  - **B-R1:** the answer locks while a check may still be held by the server and Check resends
    the same id; after only `verifier_busy` replies an edit is a new answer with a new id.
    Node controller tests + a Playwright step with real MathLive.
  - **B-R4:** the burst fails on `database_busy`/format/transport errors or zero grades;
    `measure.sh` returns that status. The recorded host run stays valid.
  - Codex's probes beside the review now pass; their cases are in normal tests.
- Thomas raised automated problem sets (not just a bank). The plan has the extraction pipeline
  (expansion queue #4); generated problems (templates or LLM) are not planned yet: decide
  with Thomas whether to add them and where.

## Resume here

1. **Deploy the review fixes** (Thomas, runbook "Update to the latest `main`"). This runs
   migration **0003**: `migrate` must show `Exited (0)`, then `/readyz` ready with `servable` 22.
   Optional: Codex re-checks the [dispositions](docs/reviews/2026-10-22-milestone-b/06-dispositions.md).
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
