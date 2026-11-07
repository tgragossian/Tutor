# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-11-06 after the answers-table live deploy.
Host runs `main` `acef550` (Explain cap, `dots` prompts, citation kinds), migration **0007**, help on.

**C1 (Claude-written, textbook-grounded help) is live as a beta with Sonnet 5.5.**
[C1 status](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md) owns release
evidence; [runbook C1](docs/ops/runbook-c1.md) has commands; [C1 rulings](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md)
records R1–R40. Milestone B is closed; actual hours are not a gate.

## Resume here

1. **Answers table is live** (0005→0007, audit PASS 26 answers/18 items/2 labels;
   [deploy record](docs/reviews/2026-11-06-answers-table/README.md#live-deploy-2026-11-06)).
   Pre-migration backup: `/srv/backups/mathtutor-pre-answers-live-20261106T232913Z.db`
   (the `...T231804Z.db` file is zero bytes). Pending: Thomas's browser check in the
   [runbook](docs/ops/runbook-answers-table.md#thomass-live-acceptance-check); confirm a
   live wrong answer gets a `mistake_type`. [Findings](docs/reviews/2026-11-06-answers-table/03-findings.md).
   Thomas's 2026-11-06 test: storage, order, hint lock and per-type ladder work. Queue:
   (a) classifier labels the same mistake differently (`15x^2+1` algebra vs `+2/+3`
   rule_misapplied), so the ladder climbs less; (b) three citations all read "§3.3": label
   example vs text; (c) hints say "the example" without naming it; (d) the answer prompt
   shows raw `y=\dots`. Explain is capped at 3 per problem (`MAX_EXPLAINS`), fixed text after.
2. **[Baseline ladder plan](docs/superpowers/plans/2026-11-06-baseline-ladder/README.md):**
   (plain request vs paste-in prompt vs tutor without textbook vs full tutor, with cost per
   useful hint). [Codex review](docs/reviews/2026-11-06-baseline-ladder/README.md)
   recommends revisions before implementation or paid runs.
3. **[Repo cleanup](docs/superpowers/plans/2026-11-06-repo-cleanup/README.md):**
   (old worktrees, ~140 stale docs, 8 review scripts; tag first, delete, `docs/history.md`).
   [Codex disposition](docs/reviews/2026-11-06-repo-cleanup/README.md): 40 superseded draft
   pages and one empty probe stub removed on this branch; other candidates retained.
4. Keep the four-arm [baseline comparison](docs/superpowers/plans/2026-11-06-baseline-ladder/README.md)
   planned for today's submission; no paid benchmark result is claimed. Update the review
   and README deployment status after Thomas's browser test.
5. [C1 release review](docs/reviews/2026-11-06-c1-release/01-findings.md) and
   [tuning list](docs/superpowers/plans/portfolio-mvp/milestone-c/c1/22-tuning.md) retain
   R40, holdout, gate-miss and load evidence. Do not attribute it to the new ladder.
6. The key belongs only in host `deploy/.env`; console spend limit on, auto-reload off.
   Turn help off with `MATHTUTOR_HELP_GENERATOR=off` if needed. Do not put keys in git.
7. Then review/rebase C2 (`milestone-c2`, owner decisions Q1–Q9; ratings and completion-only
   Clear history) and C3 own problems (resolve C-P3 first). Sequence: **C → LoRA experiment
   → D/E → expansion** (C-O4). Qwen serving: RunPod; training: AWS.

## C concepts to preserve

- Sonnet 5.5 is the C1 beta choice (R39), released with disclosed gate misses. Haiku was the
  default candidate before the measured comparison.
- Whole-book teaching corpus, offline reproducible build, BM25 first, own chunk-ID citations.
  This is explanation retrieval, not an automated graded bank or LoRA training corpus.
- Reveal is the only intentional answer path. The guard checks supported extracted math;
  it cannot guarantee no prose or cumulative leakage. Hints-only C3 lacks a reference guard.
- C1 has bounded model-LaTeX parsing, tri-state guard decisions, request/revision checks,
  deletion epochs and durable usage. Typed own-problem solving remains C3 work.
- C1 clears help text while retaining usage; C2's completion-only history behavior is planned.
  Local upload cleanup does not delete provider copies; C3 needs HEIC conversion, decoded-size
  bounds and task/variable/domain confirmation before admitting a derivative for grading.
- Evaluate raw and delivered help, including useful coverage. The C1 holdout is now regression
  evidence; reserve a separate untouched LoRA/E final set.

## Documentation tree

- [Removed draft recovery](docs/history.md): superseded original practice-loop pages at
  `archive-2026-11-06`; current contracts and dated evidence remain in the tree.
- [C1 debugging](docs/ops/debugging/c1/README.md) and [release review](docs/reviews/2026-11-06-c1-release/README.md).
- [C plan](docs/superpowers/plans/portfolio-mvp/03-rag.md), [C spec](docs/superpowers/specs/2026-10-26-milestone-c/README.md),
  [C review](docs/reviews/2026-10-26-milestone-c/README.md) and [open register](docs/superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md).
- [Source/model decision](docs/decisions/0004-rag-source-models-and-evaluation.md),
  [tutoring-data decision](docs/decisions/0005-tutoring-datasets-and-fine-tuning.md),
  [AI handoff](docs/superpowers/plans/portfolio-mvp/06-ai-decisions-handoff.md).
- [Historical handoff](docs/handoff/README.md) and [B evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md).

## Live practice loop and B evidence

- Site: https://tutor.thomasgragossian.dev · accounts, three derivative topics, 22 reviewed
  problems, MathLive, proof-based SymPy grading and history. Thomas reported `/readyz` healthy,
  22 servable problems and migrations through 0005 after the C1 deployment.
- [B status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md),
  [B review](docs/reviews/2026-10-22-milestone-b/06-dispositions.md),
  [verifier result](evals/verifier/results/README.md): development FA 0/50, FR 0/49,
  coverage 49/49 and agreement 136/136; not a frozen final benchmark.
- The host remains 1 GB (C1 memory measured 78%); CPU contention under help load is open.
  Use the [runbook](docs/ops/runbook.md); migrate must exit 0. Never `compose down -v`.

## Working rules

- Development-context Markdown stays at most 100 lines; split by responsibility and link
  from a parent. The reader-facing README is exempt.
- Keep one owner per contract; preserve historical reviews. Never relax false-accept or
  containment gates, or describe partial leak detection as proof.
- No assistant co-author trailers; assistance is acknowledged in [README](README.md#how-this-was-built).
- Actual hours are optional owner records; never infer them from agent runtime.
- Windows/OneDrive: `UV_LINK_MODE=copy`; explicit UTF-8 and raw strings for LaTeX.
  Playwright MathLive input needs `{delay: 80}`; `.superpowers/` is ignored scratch.
