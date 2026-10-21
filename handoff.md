# Calculus Tutor handoff: main checkout

Owner: Thomas Gragossian. Updated: 2026-10-21 after reading milestone B through d428bd7.

## Where current work lives

Active worktree: `.claude/worktrees/milestone-b`, branch `milestone-b`.
Its `handoff.md` and `docs/README.md` are the current documentation entry points.
The documentation sync is in that worktree; main retains the verifier-only implementation.
For the committed branch handoff: `git show milestone-b:handoff.md`.
For uncommitted documentation updates, read the worktree files directly.

## Current project state

- Tasks 1–9 are complete and merged to `main` in 102a22f: bounded SymPy verifier,
  reviewed development evaluation and CI gates.
- Tasks 10–14 are complete on `milestone-b` (d865179..c52305d): store, accounts,
  practice service, JSON API and MathLive pages. The prior handoff records them as not pushed.
- Task 15 is partial: smoke script and e2e CI job in 5fd8952; six reviewed problems remain.
  The additional 14–24 problems and Thomas's review are pending.
- Task 16 has not started. The branch container needs database migrations/storage before
  readiness succeeds; host memory measurements and deployment are still required.
- Last recorded live check (2026-10-20): milestone A skeleton, health/readiness both 200.
  No fresh live probe or milestone B deployment is claimed by this documentation update.

## Next action

Continue in `milestone-b`, at task 15 content sourcing/review, then task 16 release work.
The branch handoff records a pending choice between author-written adapted items,
human-transcribed statements or a permitted source. This docs pass makes no sourcing decision.
Do not restart task 10 from the older main plan snapshot.

## Evidence and documentation tree

- [Main documentation snapshot](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B snapshot](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Reviewed verifier evidence](evals/verifier/results/README.md): FA 0/50 (95% upper bound 7.1%),
  FR 0/49, coverage 49/49, agreement 136/136. These are development-set results.
- The branch's `07-verification-evidence.md` separates reported local app tests from old CI.
  Its `docs/ops/debugging/README.md` links application and release troubleshooting.
- Main's older task recipes describe its implementation snapshot; current completion,
  app rulings and debugging documentation live in the branch until merged.

## Working rules

Keep Markdown at most 100 lines and link each child from a parent index.
Preserve [historical references](docs/handoff/README.md) and [dated reviews](docs/reviews/README.md).
Never relax false-accept or containment gates. Record actual effort in [hours](docs/ops/hours.md).
No assistant co-author trailers; [README](README.md#acknowledgments) acknowledges assistance.
