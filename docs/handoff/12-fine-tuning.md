[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 378–404. Review findings remain unresolved.

## 6. Model Fine-Tuning

Fine-tuning is a possible future experiment, not an MVP dependency.

Potential tutoring dataset:

- MathDial

Potential approaches:

- Supervised fine-tuning
- LoRA / QLoRA

Proposed experiment:

1. Pretrained LLM + RAG
2. Pretrained LLM + RAG + explicit tutoring instructions
3. Fine-tuned LLM + RAG

Compare mathematical correctness, hint quality, solution leakage, and responsiveness to student mistakes.

Do not assume fine-tuning improves the system.

Fine-tuning should target tutoring behavior rather than attempt to replace mathematical reference retrieval.

TensorFlow is not required. PyTorch-based tooling may be more suitable for open-source LLM fine-tuning.

<!-- End preserved source. -->
