# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-22, AI decisions/documentation sync after the B deploy.
This is the main checkout handoff; `3284327`'s AI notes were read locally from `milestone-b`.
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

- Task 15: all 16 drafts approved (3c0141c), giving 22 deployed problems. Selection/practice
  tests pin the original six (`tests/support/content.py`); container smoke skips ahead to 221.
- Task 16: pool settings, load/memory tools, production-image browser CI and verifier docs.
  [B status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md) owns commits and evidence.
- Review fixes ca54407/04de2d2: durable recovery identity/revision, submission-time timing,
  ambiguous-retry UI and load-error rejection. The recovery departures and populated migration
  are rechecked; [dispositions](docs/reviews/2026-10-22-milestone-b/06-dispositions.md) owns details.
- Automated problem sets remain unplanned; [C-O4](docs/superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md)
  tracks Thomas's scope/order decision separately from expansion queue #4 (extraction).

## Resume here

1. **Done 2026-10-22:** review fixes deployed (8057590, migration 0003); Thomas confirmed healthy.
2. **Host sizing: deferred by Thomas (2026-10-22).** Stay on 1 GB, pool 1 worker / 384 MB, as a
   recorded exception: the worst-case rule (≈973 MiB > 85% of 1 GB) fails, but measured use
   leaves ≥ 281 MiB free under the burst ([host sizing](docs/ops/host-sizing.md)). Revisit in
   milestone C once retrieval's memory is known (BM25/index and any embedding setup).
   Qwen base/LoRA is planned on RunPod Serverless; training is on AWS, separate from this host.
   Not a blocker for closing milestone B.
3. Record actual hours with Thomas ([hours](docs/ops/hours.md)); 30-hour checkpoint pending.
4. [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md): verifier is
   slow on wrong answers to nested trig (`sin(cos 7x)`); `content_check` lacks a hard deadline.
5. **Next: C design session → C → LoRA → D/E → expansion.** Read the
   [AI handoff](docs/superpowers/plans/portfolio-mvp/06-ai-decisions-handoff.md); its doc-update list is complete.
   [C plan](docs/superpowers/plans/portfolio-mvp/03-rag.md) links help, evaluation, open choices and debugging.
   [0004](docs/decisions/0004-rag-source-models-and-evaluation.md): OpenStax citations, BM25 first,
   GPT-5.2 baseline vs Claude 5.5 candidates, Muse Spark dropped; evaluate hint behavior.
   [0005](docs/decisions/0005-tutoring-datasets-and-fine-tuning.md): three help buttons, dataset splits,
   Qwen3.5-9B QLoRA, paired offline and descriptive live A/B, AWS training/RunPod serving.
   [Open register](docs/superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md): serving test,
   proposed training alternative, host sizing, automated sets, API access and C design details.

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
- Historical recheck at f3a4e40: 904 Python / 3 skips, 26 Node; original/recovery/migration
  probes pass. Its B-R4 failure was fixed later in 04de2d2; see dispositions for later evidence.
  This documentation sync reruns docs/link/whitespace checks only; it is not a new runtime review.
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
