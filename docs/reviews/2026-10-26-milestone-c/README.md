# Milestone C concept review — 2026-10-26

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [C spec](../../superpowers/specs/2026-10-26-milestone-c/README.md)

Reviewed baseline: `8126fc3`, clean working tree before this review. Scope: C concepts,
consistency with the implemented B interfaces, and implementation prerequisites.
The C design and high-level sequence exist; a task-by-task implementation plan does not.
No C code, paid inference, deployment, upload processing or model evaluation was performed.

## Assessment

The C1 → C2 → C3 split, BM25 baseline, provider-neutral output schema and deterministic
grading boundary are sound. The original design overstates leak prevention and understates
the new parser, lifecycle, accounting and solver work. Proceed to implementation planning
using the amended spec; do not treat this review as release approval or runtime evidence.
Technical corrections below are review amendments, not newly attributed owner decisions.

## Findings and disposition

| ID | Priority | Finding | Documentation disposition / remaining work |
|---|---|---|---|
| C-R1 | P1 | Grader result is not a leakage verdict; no runtime LaTeX parser | [Guard](01-guard.md); explicit adapter and tri-state guard required |
| C-R2 | P1 | Help can race revisions, duplicate charges and history clearing | [State](02-state-and-cost.md); reservation/finalization contract added |
| C-R3 | P1 | Logged-cost cutoff permits concurrent overspend and reset by deletion | [Accounting](02-state-and-cost.md); separate durable reservations required |
| C-R4 | P1 | Arbitrary derivative text is not a supported solver task | [Own problems](03-intake.md); typed task and admission gates added |
| C-R5 | P1 | Local deletion is conflated with provider retention | [Intake](03-intake.md); honest privacy boundary and bounded conversion added |
| C-R6 | P1 | Final-set reuse and an OR selection rule can invalidate conclusions | [Evaluation](04-evaluation.md); split protocol and unresolved gates recorded |
| C-R7 | P2 | Stable IDs and citation validity do not prove reproducibility/support | [Retrieval](05-retrieval.md); snapshot and relevance contracts added |
| C-R8 | P2 | Active docs disagree on scope, B closure and delivery order | Synced active indexes and C children; preserved historical decisions |

P1 means resolve in the relevant slice's plan before implementation/release, not a newly
discovered vulnerability in the deployed B application. Documentation dispositions do not
mean C-R1–C-R7 are implemented or experimentally validated.

## Navigation and evidence

- [Guard](01-guard.md): extraction, parser, domain semantics, unsupported math and leakage.
- [State and cost](02-state-and-cost.md): idempotency, stale results, deletion and quotas.
- [Intake](03-intake.md): typed tasks, domains, uploads and provider retention.
- [Evaluation](04-evaluation.md): partitions, selection, abstention and human judging.
- [Retrieval](05-retrieval.md): corpus coverage, provenance, citation support and scope.
- [Validation](06-validation.md): source inspection, external references and actual checks.
- [Open register](../../superpowers/plans/portfolio-mvp/milestone-c/03-open-decisions.md): remaining planning decisions.

Recommended next action: write C1 tasks against the amended contracts, resolving C-P1/C-P2
before paid evaluation or public help. C3-specific C-P3 can wait until its task plan.
