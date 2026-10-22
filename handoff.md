# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22, after the review-fix deploy.
`main` and `milestone-b` are identical. Implementation worktree: `.claude/worktrees/milestone-b`.
The host runs `main` 8057590 (Thomas deployed; migration 0003 applied).

**Milestone B status:** B-R1/B-R2/B-R3/B-R5 verified fixed by Codex; B-R4's remaining case
(verifier crash counted as graded) fixed in 04de2d2. All fixes deployed. To close B: log hours.
Host sizing stays deferred to milestone C under Thomas's recorded exception.

## Live site (https://tutor.thomasgragossian.dev)

- Practice loop from `main` 8057590: accounts, practice on three derivative topics with MathLive,
  22 reviewed problems (7 + 7 + 8), history with "Clear history". `/readyz` ready, `servable` 22;
  migrations 0001–0003.
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
- Review fixes ca54407: migration 0003 adds reserved revision/lease/lease time; recovery
  uses the original revision, lease-aware cleanup and UUID/presentation checks. Timing ends
  at submission; UI preserves ambiguous retries. Details: [dispositions](docs/reviews/2026-10-22-milestone-b/06-dispositions.md).
- [Codex recheck](docs/reviews/2026-10-22-milestone-b/07-recheck.md): accepts any legitimate
  holder finalizing and omission of AUTOINCREMENT; both have direct passing probes.
  Populated 0002→0003 upgrade preserves old answers/results and foreign keys.
  Original five probes pass. B-R4 still drops verdict reasons: all-crash HTTP 200 responses
  count as graded work and exit 0. Database/format/transport checks and shell propagation work.
- Thomas raised automated problem sets (not just a bank). The plan has the extraction pipeline
  (expansion queue #4); generated problems (templates or LLM) are not planned yet: decide
  with Thomas whether to add them and where.

## Resume here

1. **Done 2026-10-22:** review fixes deployed (8057590, migration 0003); Thomas confirmed healthy.
2. **Host sizing: deferred by Thomas (2026-10-22).** Stay on 1 GB, pool 1 worker / 384 MB, as a
   recorded exception: the worst-case rule (≈973 MiB > 85% of 1 GB) fails, but measured use
   leaves ≥ 281 MiB free under the burst ([host sizing](docs/ops/host-sizing.md)). Revisit in
   milestone C once retrieval's memory is known (local embeddings/index vs API). A fine-tuned
   model will not run on this host at any size; plan it on a provider or separate GPU box.
   Not a blocker for closing milestone B.
3. Record actual hours with Thomas ([hours](docs/ops/hours.md)); 30-hour checkpoint pending.
4. [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md): verifier is
   slow on wrong answers to nested trig (`sin(cos 7x)`); `content_check` lacks a hard deadline.
5. **Next: milestone C (RAG hints)**, per the [delivery plan](docs/superpowers/plans/portfolio-mvp/03-rag.md).
   [Decision 0004](docs/decisions/0004-rag-source-models-and-evaluation.md) (Thomas, 2026-10-22):
   OpenStax text may go to a hosted LLM (CC licence; AI clause a recorded risk); GPT-5.2 is the
   baseline vs Claude Opus/Sonnet/Haiku 5.5; evaluate hint behaviour on hard cases. Next: design session.
   [Decision 0005](docs/decisions/0005-tutoring-datasets-and-fine-tuning.md): train LoRA on non-calculus
   TutorBench + Eedi (Thomas: fair use; weights unpublished, git-ignored); TutorBench Calculus,
   TutorMoments and C cases are evaluation only. Help type chosen by buttons (decided);
   Muse Spark added as a candidate (0004). Open: fine-tuning timing.
   Fine-tuning (LoRA) stays last in the [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md).

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
- Fresh recheck: 904 Python passed / 3 platform skips, 26 Node passed; lint/format/types/docs
  passed. Original probes and added recovery/migration probes pass; new B-R4 probe fails.
  No fresh browser, Docker, production or verifier CLI run; see [recheck](docs/reviews/2026-10-22-milestone-b/07-recheck.md).
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
