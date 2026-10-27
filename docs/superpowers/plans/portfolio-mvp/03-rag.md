# C — evaluated textbook-grounded hints

[Plan index](README.md) · Budget: 40 hours for C1; about 70–90 hours for C1–C3.

Status: design agreed 2026-10-26; the [C design spec](../../specs/2026-10-26-milestone-c/README.md)
owns exact contracts and slices C1–C3. [Concept review](../../../reviews/2026-10-26-milestone-c/README.md)
completed against `8126fc3`; review amendments are incorporated. [C1 implementation plan](milestone-c/c1/README.md) written
2026-10-26 (proposes C-P1/C-P2 values); awaiting Thomas's review. [C2 plan](milestone-c/c2/README.md) drafted 2026-10-27
(decisions Q1–Q8 await Thomas). C3 plan not written.
Accepted decisions: [0004](../../../decisions/0004-rag-source-models-and-evaluation.md)
and [0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md).
Sequence: C → LoRA experiment → D/E → [expansion queue](05-expansion-queue.md).

## Planning and debugging tree

- [Help contract](milestone-c/01-help-contract.md): buttons, context, citations, leak guard and logging.
- [Evaluation](milestone-c/02-evaluation.md): retrieval, generators, held-out splits and A/B evidence.
- [Open decisions](milestone-c/03-open-decisions.md): design-session inputs and unresolved choices.
- [Debugging](milestone-c/04-debugging.md): planned failure paths and evidence to collect.
- [AI handoff](06-ai-decisions-handoff.md): source provenance and completed documentation sync.

## Build sequence

1. Snapshot whole-book OpenStax teaching pages with explicit completeness/provenance checks.
2. Build offline from saved pages; preserve mathematical notation, assumptions and anchors.
3. Chunk by mathematical content boundaries; keep stable chunk IDs and source URLs.
4. Implement BM25 as the first retrieval baseline.
5. Add durable request/spend reservations, three buttons, Generator adapter, bounded parser/guard and safe citations.
6. Evaluate C1 under fixed retrieval and predeclared gates; measure mixed help/grading load and memory.
7. Add C2 item-scoped questions, then C3 typed/uploaded confirmed tasks with separate acceptance cases.

Resolve C-P1/C-P2 for C1 and C-P3 for C3 in the [open register](milestone-c/03-open-decisions.md).
This is a conceptual sequence, not a completed task-by-task implementation plan.

This is an explanation-ingestion pipeline, not bulk exercise extraction.
Do not let generated candidate exercises enter the graded bank without review.
Keep retrieval/prompt/provider settings in reproducible configurations.

## Tutor contract

“What did I do wrong?” gives feedback on work; Hint uses the progressive ladder;
“Explain this” uses a short confusion list. No classifier is needed for these buttons.
The server adds problem/attempt context and SymPy-checked recorded misconceptions.
Each hint cites its OpenStax section/link and licence; only server-owned source IDs resolve.
At every level, block recognized equivalent or unchecked math; Reveal is the intentional answer path.
Prose/cumulative leakage remains a measured limitation; hints-only C3 has no reference guard.
Record help type, hint level, assigned A/B arm and actual serving model separately.
The [help contract](milestone-c/01-help-contract.md) owns exact planned behavior and limits.

C initially uses the hosted winner; after LoRA, fallback is assigned RunPod base/LoRA →
hosted C model → “hints unavailable”. Practice and deterministic grading remain usable.
Set request/output limits, timeouts, per-user rate limits and a global budget before public use.

## Evaluation gate

Follow [evaluation gates](milestone-c/02-evaluation.md): Claude Haiku 5.5 versus Sonnet 5.5
(Anthropic only, 0004 §2 amended 2026-10-26). Choose Haiku unless Sonnet is better on hint
behavior beyond a margin fixed before the run, with safety/useful-coverage constraints. Neither ships if both fail.
Retrieval uses Recall@k/MRR; tutoring measures leakage, error-specific help, mistaken-reasoning
endorsement and citation support, with Wilson intervals. SymPy owns answer correctness.
Freeze C release cases before model/prompt selection; keep a separate untouched LoRA/E final set.
Dense/hybrid is an optional challenger, promoted only by controlled development evidence.

## Demo gate

A student submits a wrong derivative and receives a grounded hint with a working citation.
The hint addresses that attempt without immediately disclosing the full answer.
Show one successful interaction and one honest abstention/failure case in the demo.
