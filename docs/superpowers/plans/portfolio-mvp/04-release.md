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
Bulk extraction follows the [expansion queue](05-expansion-queue.md); use the curated subset here.

## E — final evaluation and presentation

- Grow verifier coverage toward at least 300 cases across supported types and traps.
- Report human cases and generated related cases separately.
- Run the frozen calculus retrieval/tutoring set once final choices are fixed.
- Publish denominators, abstentions, correctness, citation support, leakage and latency.
- Present a short ablation table plus failure examples and known limitations.
- Add public demo/API documentation, local startup instructions and a short demo video.
- Give every result a code/content/model/config version and reproducible command.

Never fill a resume bullet with planned features or invented improvement percentages.
Possible evidence-backed bullet structure after shipping:
“Deployed a Calculus I tutoring API with reviewed exercises and citation-grounded hints;
evaluated [N] held-out cases and measured [metric] at [latency/cost].”
Replace every bracket with a measured, clearly defined result.

## Later fine-tuning experiment

Runs directly after milestone C ([decision 0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md) §6,
amending the earlier "after extraction" order). C's baseline must be published and reproducible.
Train a small LoRA adapter with PyTorch/Hugging Face tooling on a licensed dataset.
Target hint behaviour, not calculus correctness ([decision 0004](../../../decisions/0004-rag-source-models-and-evaluation.md) §4).
Datasets, TutorBench split and unpublished weights: [decision 0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md).
Separate training, development and evaluation by original problem/conversation.
Compare the same base model before/after adaptation, with fixed retrieval and decoding.
Use held-out calculus interactions to measure transfer from MathDial.
Report training resources, seed/config, checkpoints, gains, regressions and uncertainty.
A useful negative finding still demonstrates experimental judgment.

## Completion evidence

The project is complete for this milestone when another developer can run it,
a reviewer can use the live practice-and-hint flow, and the published measurements
can be traced to versioned evaluation artifacts. Feature breadth can expand afterward.
