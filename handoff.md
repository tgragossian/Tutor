# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-28, C1 debugging fixes and documentation continuation.
Host deployment remains Thomas's reported `main` 8057590, migration 0003. No new host probe.
This checkout remains `main` at `292cee4`; C1 was rechecked in its worktree at `b16a206`.

**Milestone B is closed.** Thomas removed actual hours as a gate on 2026-10-26.
Host sizing remains C-O3; Thomas allows 2 GB if measurement needs it.

**C1 is implemented on `milestone-c1`, reviewed, and not released.** That branch's
`handoff.md` and `docs/reviews/2026-10-27-milestone-c1/README.md` own its current status:
all nine findings closed in local code; owner release gates remain. C1 is not merged here.

## Resume here

1. Claude: work on `milestone-c1`; follow its
   `docs/reviews/2026-10-27-milestone-c1/11-debugging-fixes.md`.
   R4/R7 are fixed on that branch. Follow owner release gates; carry these fixes into C2.
2. Preserve the [C concept review](docs/reviews/2026-10-26-milestone-c/README.md) as historical
   design context. Record C1 fixing commits/tests and update its handoff before owner gates.
3. C2 planning is on `milestone-c2`; Q1–Q9 are decided. Review/rebase after C1 closure; C3 needs C-P3.
4. Accepted sequence remains **C → LoRA experiment → D/E → expansion**. Automated Calc 1
   graded sets need a broader checker/review; Thomas placed them after the LoRA (C-O4,
   2026-10-26). Thomas supplies Anthropic access via secrets config (C-O5).
5. Measure corpus/index and mixed help/grading memory for C-O3; include decoder load in C3.
   Qwen serving is on RunPod, training on AWS, separate from the web host; no compute launched.

## C concepts to preserve

- Anthropic only: Haiku 5.5 default candidate, Sonnet only after a predeclared quality comparison.
  Public model documentation was checked; account access, execution prices and results were not.
- Whole-book teaching corpus, offline reproducible build, BM25 first, own chunk-ID citations.
  This is explanation retrieval, not an automated graded bank or a corpus for LoRA training.
- Reveal is the only intentional answer path. The guard checks supported extracted math;
  it cannot guarantee no prose/cumulative leakage. Hints-only C3 has no reference guard.
- The existing verifier accepts bounded MathJSON. Runtime model-LaTeX parsing, leak-specific
  results and typed derivative solving are new work, not already provided by the current pool.
- C needs request IDs/revision checks, deletion epochs and independent durable usage records.
  B's Clear history hides sessions; C's private-text deletion requires additional implementation.
- Local upload cleanup does not delete provider copies. HEIC conversion and decoded-size bounds
  are required; confirm task/variable/domain before admitting a supported derivative for grading.
- Evaluate raw and delivered help, including useful coverage. C's release holdout becomes
  regression evidence afterward; keep a separate untouched LoRA/E final set.

## Documentation tree

- C1 branch: `docs/reviews/2026-10-27-milestone-c1/11-debugging-fixes.md` owns current evidence;
  `docs/ops/debugging/c1/README.md` maps generation/guard → state/cost → evaluation.
- [C plan](docs/superpowers/plans/portfolio-mvp/03-rag.md): sequence and links to exact contracts.
- [C spec](docs/superpowers/specs/2026-10-26-milestone-c/README.md): components → help → guard → intake
  → acceptance; children own state/accounting, corpus, evaluation protocol and provider evidence.
- [C review](docs/reviews/2026-10-26-milestone-c/README.md): guard → state/cost → intake → evaluation
  → retrieval → validation. Findings are documentation dispositions, not implemented fixes.
- [Open register](docs/superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md): C-O1–C-O6 owner choices
  and C-P1–C-P4 implementation prerequisites; no unresolved choice is silently approved.
- [0004](docs/decisions/0004-rag-source-models-and-evaluation.md) and
  [0005](docs/decisions/0005-tutoring-datasets-and-fine-tuning.md): accepted source/model/data/order decisions.
- [AI handoff](docs/superpowers/plans/portfolio-mvp/06-ai-decisions-handoff.md): provenance/navigation.

## Live practice loop and B evidence

- Site: https://tutor.thomasgragossian.dev · accounts, three derivative topics, 22 reviewed
  problems (7 + 7 + 8), MathLive, proof-based SymPy grading and history.
- Thomas reported healthy `/readyz`, `servable` 22 and migrations 0001–0003 after deployment.
  Initial `/readyz` can return 502 for 30–60 s while workers start.
- [B status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md) owns completed tasks.
  [B review dispositions](docs/reviews/2026-10-22-milestone-b/06-dispositions.md) owns fix chronology.
- [Verification evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  separates historical CI/browser/host evidence from local checks. C review reruns docs checks only.
- [Reviewed verifier result](evals/verifier/results/README.md): dev FA 0/50 (95% upper bound 7.1%),
  FR 0/49, coverage 49/49, agreement 136/136; not a frozen final benchmark.
- [Follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md): slow nested-trig
  wrong answers and `content_check` without a hard deadline remain recorded cleanup.
- Stay on 1 GB, pool 1 / 384 MB under the recorded [host-sizing exception](docs/ops/host-sizing.md).
  Thomas deploys through the [runbook](docs/ops/runbook.md); migrate must exit 0. Never `compose down -v`.

## Working rules

- Every Markdown file stays at most 100 lines; split by responsibility and link from a parent.
- Keep one owner per contract; preserve [historical handoff](docs/handoff/README.md) and dated reviews.
- Never relax false-accept or containment gates; never describe partial leak detection as a proof.
- No assistant co-author trailers; assistance is acknowledged in [README](README.md#acknowledgments).
- Actual hours are optional owner records; never infer them from agent runtime.
- Windows/OneDrive: `UV_LINK_MODE=copy` for `uv add`; explicit UTF-8 and raw strings for LaTeX.
  Playwright MathLive input needs `{delay: 80}`. Local `.superpowers/sdd/README/progress.md` is ignored;
  tracked [app rulings](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md) own B decisions.
