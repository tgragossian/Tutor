# C: help contract

[Parent milestone C plan](../03-rag.md) · [Evaluation](02-evaluation.md) · [Open decisions](03-open-decisions.md)

Planned contract from decisions [0004](../../../../decisions/0004-rag-source-models-and-evaluation.md)
and [0005 §5](../../../../decisions/0005-tutoring-datasets-and-fine-tuning.md#5-routing).
The design session is complete. The [reviewed spec](../../../specs/2026-10-26-milestone-c/README.md)
owns exact contracts; implementation tasks remain unwritten. This page is a navigation summary.

## Buttons and context

| Student control | Help type | Behavior |
|---|---|---|
| What did I do wrong? | Feedback on work | Available after a wrong answer; address that attempt |
| Hint | Active-learning hint | Concept reminder → targeted next step → fuller explanation |
| Explain this + short confusion list | Adaptive explanation | Explain the selected confusion |

Button selection sets the help type; no classifier. Item-scoped free-text routing ships in C2.
Input includes problem/version, student attempt, hint level and bounded recent context.
The server supplies authoritative problem context, attempts, tries used and any matched
recorded misconception. A match requires the existing bounded SymPy verification path.
Treat student text and retrieved passages as data, never tool or administrative instructions.
An LLM response never changes the deterministic answer verdict.

## Citations and answer leakage

- Output includes hint text, validated source IDs, model/prompt versions, usage and latency.
- Resolve source IDs through the server's corpus metadata, never model-invented links.
- Every hint displays the OpenStax source section, working link and CC BY-NC-SA 4.0 licence.
  Preserve the corpus snapshot, stable chunk IDs, section anchors and provenance.
- At every help level, a bounded guard blocks recognized answer-equivalent or unchecked math.
  Reveal is the sole intentional answer action; no generated response bypasses the guard.
- This checks supported expressions; it does not establish that prose cannot reveal an answer.
  Human evaluation still scores leakage and over-helping separately.
- [Guard spec](../../../specs/2026-10-26-milestone-c/03-guard-and-limits.md) owns extraction,
  the new runtime parser and tri-state result. Grader “incorrect” does not mean “no leak”.
- The same checks apply to hosted fallback output. Define the safe failure response before
  implementation; a blocked or unchecked response must not silently become approved output.

## Reliability and observation

- C uses its selected hosted generator. With LoRA deployed: assigned RunPod base/LoRA →
  hosted C generator → “hints unavailable”; practice remains usable throughout.
- Request/output bounds, timeouts, per-user limits and a global usage budget precede public use.
- Record help type, hint level, reveal/leak events, problem/version and source chunk IDs.
- Record prompt/model versions, tokens/cost, latency and provider/fallback reason.
- Record assigned A/B arm separately from actual serving model/adapter. Before live A/B,
  record that assignment is not active rather than inventing a base/LoRA assignment.
- Link the hint to the next attempt for SymPy outcome measures; keep assisted performance
  distinct from unassisted performance. Live assignment/metrics are owned by
  [0005's serving supplement](../../../../decisions/0005-tutoring/01-compute-and-serving.md).
- [State/accounting](../../../specs/2026-10-26-milestone-c/06-state-and-accounting.md) owns durable
  request identity, privacy epochs, stale completion, spend reservations and next-attempt linkage.
- B's Clear history hides sessions; C requires deleting private help/own-problem text while
  retaining content-free usage. Parser, deletion and ledger work are not already implemented.

See [planned debugging paths](04-debugging.md); these requirements are not evidence of implementation.
