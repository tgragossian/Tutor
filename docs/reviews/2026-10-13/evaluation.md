# Evaluation and portfolio evidence

[Review index](README.md) · [Original task 10](../../superpowers/plans/core-practice-loop/tasks/10-verifier-evaluation-set-and-ci-gate.md)

## E1 — P1: generator labels are not an independent oracle

Task 10 uses SymPy both to create/check labels and as the verifier engine.
This is useful regression coverage, but shared mathematical assumptions can hide errors.
Raw expression inequality is also the wrong label test for antiderivatives:
negating a constant antiderivative changes its value but not its derivative.
Numerically rounded answers and sets need their own labeling rules.

Maintain human-reviewed labels and rationale for adversarial cases.
Generated variants supplement them; they do not establish independent accuracy.
Check labels under each answer type's semantics and domain. If a label is wrong,
correct it with a recorded rationale rather than the blanket instruction never to relabel.

## E2 — P1: separate development cases from the final evaluation

Capture real browser inputs; include singularities, near-equality, branch errors,
overflow, partial input, timeout, numeric precision and unsupported notation.
Split by source problem/family before generating variants to avoid leakage.
Keep a frozen final set outside routine prompt/rule tuning; record any later exposure.
Version datasets, content, parser, verifier and evaluation configuration.

Report conditional denominators:
FA = wrong inputs accepted / wrong inputs; FR = correct inputs rejected / correct inputs.
Report abstention separately for correct, wrong and unsupported inputs.
A reject-everything verifier must fail the supported-coverage acceptance gate.
Report sample counts and uncertainty; zero observed false accepts is not a proof.
For illustration, zero among 300 independent wrong cases has an approximate 95%
upper bound near 1%; the planned 300 total mixed/related cases justify less certainty.

## E3 — P1: CI must enforce what the release claims

Task 10 only fails CI for false accepts, although the spec promises false-reject,
inconclusive and latency limits too. Add coverage/count and FR/abstention gates.
Report speed on a named host and workload; avoid a fragile universal CI p95 threshold.
Measure API queue-inclusive latency, worker time, cold start and busy-system behavior.
Task 7's recovery test opens a new pool: test the same pool after a forced worker failure.

## E4 — RAG must show a measured reason to exist

Build 40–60 reviewed calculus questions/misconceptions with relevant passage labels.
Compare no retrieval, BM25 and dense/hybrid retrieval using the same generator and prompts.
Measure retrieval Recall@k/MRR, citation validity and whether the passage supports the claim.
Score correctness, useful next-step hints, misconception response and solution leakage
separately using a written rubric, blinded human review and a held-out problem split.
Keep task completion/learning gains separate; a small offline benchmark cannot establish them.
Store corpus hashes, chunks, model/prompt versions, token usage, cost and latency.

## E5 — MathDial is a transfer experiment

MathDial records pedagogical dialogue acts and judgments about seventh-grade interactions.
Those labels are not a calculus correctness or answer-leakage benchmark.
[Dataset documentation](https://github.com/eth-nlped/mathdial)
Use its labels to inform behavior or training, then evaluate on separate calculus cases.
Compare the same open model before/after LoRA under identical retrieval and decoding.
A hosted stronger model is a separate reference, not the causal fine-tuning baseline.
Report negative results honestly; adapter weights alone are not an MLE result.

## E6 — content validation and data provenance

Do not serve computed_only items as reliable graded assessments.
Computing an answer to a mistranscribed problem does not validate the transcription.
Record extraction version, source snapshot, review status, reviewer and source location.
Use stratified human audits by topic/notation/status; report sample sizes and error types.
OpenStax's current preface identifies CC BY-NC-SA 4.0; preserve source attribution
and track content licensing separately from code.
[OpenStax preface](https://openstax.org/books/calculus-volume-1/pages/preface)
