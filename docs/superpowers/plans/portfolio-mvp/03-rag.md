# C — evaluated textbook-grounded hints

[Plan index](README.md) · Budget target: 40 hours.

Status: design session next; the contracts below are planned, not shipped features.
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

1. Snapshot a small relevant OpenStax HTML corpus and its provenance.
2. Parse sections, definitions and examples; preserve mathematical notation and anchors.
3. Chunk by mathematical content boundaries; keep stable chunk IDs and source URLs.
4. Implement BM25 as the first retrieval baseline.
5. Add the three help buttons, one generator API, citations and the SymPy answer-leak guard.
6. Evaluate hosted generators with fixed retrieval; compare dense/hybrid against measured BM25.

This is an explanation-ingestion pipeline, not bulk exercise extraction.
Do not let generated candidate exercises enter the graded bank without review.
Keep retrieval/prompt/provider settings in reproducible configurations.

## Tutor contract

“What did I do wrong?” gives feedback on work; Hint uses the progressive ladder;
“Explain this” uses a short confusion list. No classifier is needed for these buttons.
The server adds problem/attempt context and SymPy-checked recorded misconceptions.
Each hint cites its OpenStax section/link and licence; only server-owned source IDs resolve.
Below reveal level, block an expression proven equivalent to the answer and log a leak event.
Record help type, hint level, assigned A/B arm and actual serving model separately.
The [help contract](milestone-c/01-help-contract.md) owns exact planned behavior and limits.

C initially uses the hosted winner; after LoRA, fallback is assigned RunPod base/LoRA →
hosted C model → “hints unavailable”. Practice and deterministic grading remain usable.
Set request/output limits, timeouts, per-user rate limits and a global budget before public use.

## Evaluation gate

Follow [evaluation gates](milestone-c/02-evaluation.md): GPT-5.2 baseline versus the recorded
Claude Opus/Sonnet/Haiku 5.5 candidates, Muse Spark excluded. Choose the cheapest model
non-inferior to the best on hint behavior, with a margin fixed before the run.
Retrieval uses Recall@k/MRR; tutoring measures leakage, error-specific help, mistaken-reasoning
endorsement and citation support, with Wilson intervals. SymPy owns answer correctness.
Freeze final cases before model/prompt selection; use development cases for selection.

## Demo gate

A student submits a wrong derivative and receives a grounded hint with a working citation.
The hint addresses that attempt without immediately disclosing the full answer.
Show one successful interaction and one honest abstention/failure case in the demo.
