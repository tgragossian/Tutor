# D/E — reproducibility, operations and portfolio release

[Plan index](README.md) · Budget targets: D 25 hours; E 20 hours.

## D — operating evidence

- Rebuild the corpus/index from a recorded source snapshot and configuration.
- Measure deployment memory and queue-inclusive p50/p95 latency on a named workload.
- Record model tokens, cost per interaction and provider failure/retry behavior.
- Deploy the CI-tested image identity, with a known-good rollback target.
- Restore a backup into a separate database and verify known records.
- Demonstrate restart persistence, rate limits and graceful provider/verifier failures.
- Keep deployment configuration, secrets instructions and runbook modular and short.

If helpful, add a small transparent weak-topic selection rule after the static baseline.
Do not claim its learning benefit without a separate study.
Bulk exercise extraction follows the [expansion queue](05-expansion-queue.md); C's explanation
corpus covers whole-book teaching material and remains separate from the reviewed problem bank.

## E — final evaluation and presentation

- Grow verifier coverage toward at least 300 cases across supported types and traps.
- Report human cases and generated related cases separately.
- Run the disjoint LoRA/E final calculus set in a locked paired campaign after choices are fixed.
  C's published release holdout is regression evidence, not E's untouched final set; see the
  [partition protocol](../../specs/2026-10-26-milestone-c/08-evaluation-protocol.md).
- Publish denominators, abstentions, correctness, citation support, leakage and latency.
- Present a short ablation table plus failure examples and known limitations.
- Add public demo/API documentation, local startup instructions and a short demo video.
- Give every result a code/content/model/config version and reproducible command.

Never fill a resume bullet with planned features or invented improvement percentages.
Possible evidence-backed bullet structure after shipping:
“Deployed a Calculus I tutoring API with reviewed exercises and citation-grounded hints;
evaluated [N] held-out cases and measured [metric] at [latency/cost].”
Replace every bracket with a measured, clearly defined result.

## Fine-tuning experiment: after C, before D/E

Runs directly after milestone C ([decision 0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md) §6,
amending the earlier "after extraction" order). C's baseline must be published and reproducible.
Train Qwen3.5-9B with QLoRA and PyTorch/Hugging Face tooling under the dataset decisions below.
Target hint behaviour, not calculus correctness ([decision 0004](../../../decisions/0004-rag-source-models-and-evaluation.md) §4).
Datasets, TutorBench split and unpublished weights: [decision 0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md).
Train on TutorBench non-calculus, Eedi and MathDial; hold TutorBench Calculus, TutorMoments
and milestone C cases out of training. Check task-ID/text overlap before every job.
Separate training, development and final evaluation by original problem/conversation.
A/B 1 pairs base versus LoRA with fixed retrieval/prompts/decoding; A/B 2 compares LoRA with
C's hosted winner on quality and cost. Measure transfer from TutorBench/Eedi/MathDial.
Train on AWS; serve both arms on one RunPod Serverless worker, with hosted fallback.
Keep a student's live arm fixed; log actual model/fallback and next-attempt SymPy result,
leak/reveal rates and thumbs up/down. Live results are descriptive at about 50 students.
The offline paired comparison remains the headline result. Detailed gates and partitions:
[evaluation](milestone-c/02-evaluation.md); hosting and test: [serving](../../../decisions/0005-tutoring/01-compute-and-serving.md).
Report training resources, seed/config, checkpoints, gains, regressions and uncertainty.
A useful negative finding still demonstrates experimental judgment.
This experiment has no approved hours estimate yet; re-estimate the core schedule before starting it.

## Completion evidence

The project is complete for this milestone when another developer can run it,
a reviewer can use the live practice-and-hint flow, and the published measurements
can be traced to versioned evaluation artifacts. Feature breadth can expand afterward.
