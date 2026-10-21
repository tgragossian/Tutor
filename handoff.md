# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-21 after merging `milestone-b` (tasks 10–14, review
fixes, container storage) into `main`. The `milestone-b` worktree remains for tasks 15–16:
`.claude/worktrees/milestone-b`.

## Current state

- Tasks 1–9 (bounded SymPy verifier, reviewed evaluation, CI gates) merged in 102a22f.
- Tasks 10–14 (store, accounts, practice service, JSON API, MathLive pages) are merged:
  d865179..c52305d, [rulings A1–A18](docs/superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md).
- [2026-10-21 review](docs/reviews/2026-10-21-milestone-b/README.md) B-A1–B-A5 fixed in 4eba48f
  with regression tests ([dispositions](docs/reviews/2026-10-21-milestone-b/04-dispositions.md)).
- e6da0e5 adds container storage: `/data` volume (uid 10001), a one-shot `migrate` service
  (`alembic upgrade head`) before `app`, and a container smoke that grades one real answer.
- [CI run 39657984302](https://github.com/tgragossian/Tutor/actions/runs/39657984302) on
  `milestone-b` at e6da0e5: Python, Node, browser e2e and container smoke all green.
- Task 15 is partial: browser smoke and its CI job (5fd8952); six reviewed problems remain.
  The additional 14–24 problems and Thomas's review are pending.
- Last recorded live check (2026-10-20): milestone A skeleton. The milestone B deploy is next.

## Next actions

1. **Deploy (Thomas, Lightsail browser SSH):** follow the [runbook](docs/ops/runbook.md)
   "Update to the latest `main`" block. No `deploy/.env` changes are needed. Then check
   `/readyz`, sign up and answer one problem on the live site.
2. Right after deploying, record `sudo docker stats --no-stream` and `free -m` (1 GB host);
   task 16 step 3 sizes the verifier pool from these numbers.
3. Task 15 content: choose the sourcing route. OpenStax's notice forbids feeding the book to
   LLMs: human-transcribed statements, author-written `adapted` items, or a mix.
   See [content](content/README.md) and the [source manifest](content/sources/openstax-calculus-v1.md).
4. Draft and check the new problems, then Thomas's content review (gate).
5. Rest of task 16: load tool, e2e on the image, verifier docs. Then one fresh whole-branch review.
6. Record actual hours with Thomas before the 30-hour scope/date/contingency decision.

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
