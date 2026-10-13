# C — evaluated textbook-grounded hints

[Plan index](README.md) · Budget target: 40 hours.

## Build sequence

1. Snapshot a small relevant OpenStax HTML corpus and its provenance.
2. Parse sections, definitions and examples; preserve mathematical notation and anchors.
3. Chunk by mathematical content boundaries; keep stable chunk IDs and source URLs.
4. Implement BM25 as the first retrieval baseline.
5. Add one generator API and a progressive-hint route for the current problem.
6. Compare dense/hybrid retrieval only against the measured baseline.

This is an explanation-ingestion pipeline, not bulk exercise extraction.
Do not let generated candidate exercises enter the graded bank without review.
Keep retrieval/prompt/provider settings in reproducible configurations.

## Tutor contract

Input: problem/version, student attempt, requested hint level and recent bounded context.
Output: hint text, validated source IDs, model/prompt versions, usage and latency.
Server-owned source IDs resolve to URLs; do not trust invented model links.
Treat retrieved content and student text as data, never as tool/administrative instructions.
An unavailable provider returns a clear retryable error; practice remains usable.
An LLM response never changes the deterministic answer verdict.

Use a small fixed hint ladder: concept reminder, targeted next step, fuller explanation.
Track hint/reveal events so later practice metrics distinguish assisted performance.
Choose provider/model after a small cost-quality comparison; avoid hardcoding a guessed winner.
Set request/output limits, a timeout and a global usage budget before a public demo.

## Evaluation gate

Prepare 40–60 human-reviewed calculus cases with relevance judgments before tuning.
Partition by source problem/family into development and final evaluation sets.
Compare no retrieval, BM25 and one dense/hybrid candidate under the same generator.
Report retrieval Recall@k/MRR and failures by equation-heavy versus prose questions.
Blind-score correctness, useful next step, citation support and answer leakage separately.
Include out-of-scope questions, insufficient evidence and mistaken student reasoning.
Store exact prompts/configs, corpus/index hashes, model versions and case-level results.
Document sample counts and uncertainty; choose the simpler system if improvement is unclear.

## Demo gate

A student submits a wrong derivative and receives a grounded hint with a working citation.
The hint addresses that attempt without immediately disclosing the full answer.
Show one successful interaction and one honest abstention/failure case in the demo.
