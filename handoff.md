# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-21; code reviewed at d428bd7 after the documentation sync.
Active worktree: `.claude/worktrees/milestone-b`, branch `milestone-b`.

## Current state

- Tasks 1–9 (bounded SymPy verifier and reviewed evaluation) merged to `main` in 102a22f.
- Tasks 10–14 complete on `milestone-b` (d865179..c52305d): persistence, accounts,
  practice service, JSON API and MathLive pages. The handoff records these as not pushed.
- Task 15 is partial: browser smoke and its CI job landed in 5fd8952; six reviewed
  problems remain. The additional 14–24 problems and human review are still pending.
- Task 16 has not started. The branch container lacks database storage/migration wiring;
  `/readyz` is expected to fail with `database_unavailable` until that work is done.
- Last recorded live check (2026-10-20): milestone A skeleton, `/healthz` and `/readyz`
  both 200. No milestone B deployment or fresh live check is claimed.

## Claude: address review findings before release

[2026-10-21 review](docs/reviews/2026-10-21-milestone-b/README.md) records five reproduced gaps:

- **B-A1, P1:** duplicate/stale Skip can act on the next presentation; bind actions to item IDs.
- **B-A2, P2:** deeply nested raw JSON under 16 KB escapes as 500 before structural checks.
- **B-A3, P2:** SQLite writer contention in auth/read paths escapes as 500.
- **B-A4, P2:** old presentations silently use new bundle content under their old version.
- **B-A5, P2:** late format responses after Skip can restore completed items in the browser.

Fix B-A1/B-A5 together, then input/storage/version handling; add regressions to normal tests.
The linked review contains file/line owners, proposed fixes and executable failing probes.
No production-code fixes were made; earlier uncommitted docs remain in this worktree.
Fresh checks: **839 Python passed, 1 skipped; 19 Node passed; lint/types/content passed**.
Five targeted review assertions fail on the current code. No new Docker/Linux/browser/live pass.

## After review fixes

1. Resolve task 15's content sourcing with Thomas, as recorded in the prior handoff:
   author-written `adapted` items, human-transcribed statements, or a permitted source.
   See [content](content/README.md) and the [source manifest](content/sources/openstax-calculus-v1.md).
2. Draft and mathematically check the new problems, then obtain Thomas's content review.
3. Complete task 16's migrations/volume wiring, container browser smoke, Linux memory
   measurements and deployment. See [release debugging](docs/ops/debugging/02-release.md).
4. Record actual hours with Thomas before a scope/date/contingency decision at 30 hours.

## Evidence and navigation

- [Documentation tree](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)
  owns task completion and outstanding gates.
- [Verification evidence](docs/superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md)
  separates prior browser/CI evidence from the [fresh code-review validation](docs/reviews/2026-10-21-milestone-b/03-validation.md).
- [Reviewed verifier result](evals/verifier/results/README.md): FA 0/50 (95% upper bound 7.1%),
  FR 0/49, coverage 49/49, agreement 136/136; no internal errors. This is a dev set.
- [App rulings A1–A18](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md),
  [file map](docs/superpowers/plans/portfolio-mvp/milestone-b/01-file-map.md),
  [debugging tree](docs/ops/debugging/README.md), [API contracts](contracts/README.md).
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
