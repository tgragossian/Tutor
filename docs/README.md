# Documentation

Main snapshot: tasks 1–9 merged. Current app docs live in `.claude/worktrees/milestone-b/docs`.
Read the [current handoff](../handoff.md) before continuing work: tasks 10–14 are already done
on the branch; task 15 is partial and task 16 is pending.

- [Current handoff](../handoff.md): status, priorities and next action.
- [Decisions](decisions/README.md): accepted direction and precedence.
- [Active portfolio-core spec](superpowers/specs/2026-10-13-portfolio-core/README.md): approved contracts for milestones A–B.
- [Active option B delivery plan](superpowers/plans/portfolio-mvp/README.md): milestones and gates.
  - [Milestone B tasks](superpowers/plans/portfolio-mvp/milestone-b/README.md): main snapshot through tasks 1–9; continue using the branch handoff.
  - [R24 implementation](superpowers/plans/portfolio-mvp/milestone-b/r24/README.md): scoped precision, debugging and release checklist.
- [Reviews](reviews/README.md): historical findings and the 2026-10-19 evaluation review.
- Historical references:
  - [Original handoff](handoff/README.md).
  - [Original design](superpowers/specs/2026-10-13-core-practice-loop-design.md).
  - [Original task plan](superpowers/plans/2026-10-13-core-practice-loop.md).
- [Operations](ops/README.md): hours log and operational notes.
- [API contracts](../contracts/README.md): example request and item bodies.
- [Verifier evaluation](../evals/verifier/README.md): case format, gates and commands.
  - [Reviewed results and CI](../evals/verifier/results/README.md): passing dev gate; historical drafts separated.
- [Content](../content/README.md): problem authoring, compiling and source licence manifest.

Reference documents preserve original wording and numbering for traceability.
Decision 0001 takes precedence over the approved portfolio-core spec, which takes
precedence over the original design for milestones A–B. The active plan governs
delivery order; resolve findings before implementing affected tasks.

Keep each Markdown file at most 100 lines, with a descriptive parent link.
Use JSON/CSV for full evaluation results and short Markdown summaries for readers.
