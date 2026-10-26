# Documentation

Milestone B (practice loop) and review fixes are deployed at 8057590 per Thomas; migration 0003 applied.
The load tool's verifier-crash case (B-R4) was fixed in 04de2d2. See
[dispositions](reviews/2026-10-22-milestone-b/06-dispositions.md) for fix/recheck chronology.
The hours log remains. Host sizing is deferred to C under Thomas's recorded exception.
Read the [current handoff](../handoff.md) before continuing work.

- [Current handoff](../handoff.md): status, priorities and next action.
- [Decisions](decisions/README.md): accepted direction and precedence.
- [Active portfolio-core spec](superpowers/specs/2026-10-13-portfolio-core/README.md): approved contracts for milestones A–B.
- [Milestone C design spec](superpowers/specs/2026-10-26-milestone-c/README.md): help, own problems, evaluation; under review.
- [Active option B delivery plan](superpowers/plans/portfolio-mvp/README.md): milestones and gates.
  - [Milestone B tasks](superpowers/plans/portfolio-mvp/milestone-b/README.md): tasks 1–16 and fixes deployed; hours remain.
  - [R24 implementation](superpowers/plans/portfolio-mvp/milestone-b/r24/README.md): scoped precision, debugging and release checklist.
  - [App-track rulings](superpowers/plans/portfolio-mvp/milestone-b/06-app-track-rulings.md): A1–A21; recovery ruling A14 amended and rechecked.
  - [Verification evidence](superpowers/plans/portfolio-mvp/milestone-b/07-verification-evidence.md): local checks versus historical CI.
  - [Milestone C](superpowers/plans/portfolio-mvp/03-rag.md): planned help contract, evaluation, open choices and debugging children.
  - [AI handoff](superpowers/plans/portfolio-mvp/06-ai-decisions-handoff.md): accepted decisions map and completed doc sync.
  - [LoRA compute/serving](decisions/0005-tutoring/01-compute-and-serving.md) and [cost assumptions](decisions/0005-tutoring/02-sizing-and-costs.md).
- [Reviews](reviews/README.md): dated findings and evidence.
  - [2026-10-22 code review](reviews/2026-10-22-milestone-b/README.md): prioritized fixes, modular debugging and executable probes.
  - [2026-10-21 code review](reviews/2026-10-21-milestone-b/README.md): historical issues and implemented fixes.
- Historical references:
  - [Original handoff](handoff/README.md).
  - [Original design](superpowers/specs/2026-10-13-core-practice-loop-design.md).
  - [Original task plan](superpowers/plans/2026-10-13-core-practice-loop.md).
- [Operations](ops/README.md): development setup, hours, host, runbook and security.
  - [Debugging tree](ops/debugging/README.md): symptoms, owning files and focused checks.
- [API contracts](../contracts/README.md): example request and item bodies.
- [Verifier](verifier/README.md): what it accepts, limitations and milestone B results.
- [Verifier evaluation](../evals/verifier/README.md): case format, gates and commands.
  - [Reviewed results and CI](../evals/verifier/results/README.md): passing dev gate; historical drafts separated.
- [Content](../content/README.md): problem authoring, compiling and source licence manifest.

Reference documents preserve original wording and numbering for traceability.
Accepted decisions and their later amendments take precedence over the approved portfolio-core
spec, which takes precedence over the original design for milestones A–B. Decisions 0004/0005
govern C/LoRA; the active plan reflects C → LoRA → D/E → expansion.

Keep each Markdown file at most 100 lines, with a descriptive parent link.
Keep one owner per fact: decisions for accepted direction, plans for work/status, evidence for
dated checks, operations for procedures. Cross-link instead of copying full status or cost tables.
Use JSON/CSV for full evaluation results and short Markdown summaries for readers.
