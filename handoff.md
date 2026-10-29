# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-28: C1 debugging fixes and modular docs.
Host deployment remains Thomas's reported `main` 8057590, migration 0003. No new host probe.
Branch `milestone-c1` holds C1 tasks 1-15 plus fixes; rechecked `b16a206`. Nothing merged or deployed.

**Milestone B is closed.** Thomas removed actual hours as a gate on 2026-10-26.

**C1 (Claude-written, textbook-grounded help) is implemented but not released.**
[C1 status](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md) owns the owner
checklist and gate table; [runbook C1](docs/ops/runbook-c1.md) has the commands. Rulings R1-R36
(R35 hint ladder per mistake type with a two-step level 0; R36 prompt fingerprint) are in [C1 rulings](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md).

## Resume here

1. [C1 debugging fixes](docs/reviews/2026-10-27-milestone-c1/11-debugging-fixes.md): all nine
   findings closed in local code. R4 claims holdout use before scoring; R7 preserves uncited
   baseline judging/audit/recompute. Saved probes and normal regressions
   pass. R35/R36 reviewed. Follow the owner gates below and carry these fixes into C2 before
   its plan review/implementation. No paid comparison, actual holdout or release ran.
2. After review fixes, owner steps pending: review 60 cases + 40 queries (`reviewed_by: tg`; incl.
   `expect_mistake_type`/`prior_hints`/`start_step`); approve the 12 confusion labels, 4 rewritten
   misconception notes, level/mistake-type wording, help panel copy and provider disclosure; paid dev run
   (`--max-usd 4`) and audit; **decide on the retrieval gate before the holdout** (dev
   Recall@6 0.79 < 0.80); one-shot holdout; `E2E=1 bash tests/container/smoke.sh`; container
   mixed-load measurement; deploy; live check (one cited hint on a wrong derivative, one
   abstention). Then commit `docs: C1 released`.
   Holdout cap formula and the 0.576 draft-holdout disclosure: C1 status page and runbook C1.
3. Key: `MATHTUTOR_ANTHROPIC_API_KEY` only in the host's `deploy/.env`; console spend limit,
   auto-reload off; $5 credit. Turn help off with `MATHTUTOR_HELP_GENERATOR=off`.
4. Then review/rebase C2 (plan on `milestone-c2`, Q1–Q9 decided by Thomas; adds ratings and a
   completion-only Clear history) and C3 own problems (resolve C-P3 first). The C2 worktree
   cannot build its venv yet (Windows Application Control blocks uv). Sequence remains
   **C -> LoRA experiment -> D/E -> expansion** (C-O4). Qwen serving: RunPod; training: AWS.
5. Memory: the only mixed-load numbers so far are
   [preliminary, Windows, not the gate](docs/ops/host-sizing-c1.md); 1 GB vs 2 GB is decided by
   the container run (Thomas approved 2 GB on 2026-10-26).

## C concepts to preserve

- Anthropic only: Haiku 5.5 default candidate, Sonnet only after a predeclared quality comparison.
  Public model documentation was checked; account access, execution prices and results were not.
- Whole-book teaching corpus, offline reproducible build, BM25 first, own chunk-ID citations.
  This is explanation retrieval, not an automated graded bank or a corpus for LoRA training.
- Reveal is the only intentional answer path. The guard checks supported extracted math;
  it cannot guarantee no prose/cumulative leakage. Hints-only C3 has no reference guard.
- C1 implements bounded model-LaTeX parsing, tri-state guard decisions, request/revision checks,
  deletion epochs and durable usage. Typed own-problem solving remains C3 work.
- C1 clears help text while retaining usage; C2's completion-only history behavior is planned.
- Local upload cleanup does not delete provider copies. HEIC conversion and decoded-size bounds
  are required; confirm task/variable/domain before admitting a supported derivative for grading.
- Evaluate raw and delivered help, including useful coverage. C's release holdout becomes
  regression evidence afterward; keep a separate untouched LoRA/E final set.

## Documentation tree

- [C1 debugging](docs/ops/debugging/c1/README.md): generation/guard → state/cost → evaluation.
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
  separates historical CI/browser/host evidence from local checks; C1 has its own validation page.
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
  Playwright MathLive input needs `{delay: 80}`. Local `.superpowers/` is ignored scratch; tracked
  [B rulings](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md) and
  [C1 rulings](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md) own decisions.
