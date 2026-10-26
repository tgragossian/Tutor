# C and LoRA: evaluation gates

[Parent milestone C plan](../03-rag.md) · [Help contract](01-help-contract.md)

Planned evidence, governed by [decision 0004 §3](../../../../decisions/0004-rag-source-models-and-evaluation.md#3-hint-evaluation-measures-what-models-get-wrong)
and [decision 0005 §§1–4](../../../../decisions/0005-tutoring-datasets-and-fine-tuning.md).

## Retrieval and hosted-model selection in C

1. Prepare 60 help cases (36 development/24 C release holdout) and 40 reviewed retrieval queries.
   Split by source problem/family before tuning; reserve a separate untouched LoRA/E final set.
2. Establish BM25; compare no retrieval/BM25 with one fixed generator; dense/hybrid is optional in C1.
   Promote dense/hybrid only if it improves measured Recall@k/MRR; report prose/equation failures.
3. Compare Claude Haiku 5.5 with Sonnet 5.5 under identical retrieval, prompts and limits
   (Anthropic only, 0004 §2 amended 2026-10-26; GPT-5.2 and Muse Spark are dropped).
4. Use development cases: the proposed margin is 10 percentage points; fix a primary measure,
   safety/coverage constraints and judging before comparison (C-P2). Neither ships if both fail.
5. Run C's release holdout after choices are fixed, before C ships. It then becomes regression
   evidence, never relabeled an untouched E final set. E has a separate locked paired campaign.

Model names are the accepted comparison plan; confirm callable versions and prices at execution.
[Evaluation protocol](../../../specs/2026-10-26-milestone-c/08-evaluation-protocol.md) owns exact
denominators, split lifecycle and judge audits; the [review](../../../../reviews/2026-10-26-milestone-c/04-evaluation.md)
explains the corrections. No model/retrieval evaluation has run yet.

## Hint behavior and reporting

- Primary: leakage by hint level, addressing the student's specific error, not endorsing wrong
  reasoning, and citation support. SymPy alone decides student-answer correctness.
- Blind-score useful next steps, mathematical errors in hints and appropriate abstention too.
- Deliberately include mistaken reasoning, nearly-right work, answer requests, easy level-1
  leakage traps, out-of-scope questions and insufficient evidence. Report easy cases separately.
- Score raw generations and delivered help, including useful coverage and guard false blocks.
  Always-abstain must fail coverage. Audit the random human sample plus flagged failures.
- Report marginal counts/Wilson intervals and paired, family-grouped comparisons; a null result is a finding, not evidence
  of superiority. Choose the simpler retrieval system if improvement is unclear.
- Record exact prompts/configs, corpus/index hashes, model versions, prices, tokens, latency
  and case-level scores. Keep full machine-readable results outside short Markdown summaries.

## LoRA directly after C

- Publish C's reproducible baseline first. Use Qwen3.5-9B with one QLoRA adapter for all help types.
- Training: TutorBench non-calculus, Eedi and MathDial. Qwen generates training responses;
  version the rubric judge, prompts, scores and response selection.
- Evaluation only: TutorBench Calculus (258), TutorMoments and milestone C cases.
  Never use these as training examples or to select training responses. Check task-ID/text
  overlap before every training job; split related problems/conversations together.
- Preserve a disjoint untouched LoRA/E final partition. C's published release holdout is only
  a regression set, excluded from training/selection; fix partitions before experimentation.
- A/B 1: paired Qwen base vs base + LoRA, same retrieval, prompts and decoding; headline result.
- A/B 2: LoRA vs C's hosted winner, quality and cost per hint; separate reference comparison.
- Report seed/config, checkpoints, training resources, uncertainty and regressions per help type.
  Measure transfer from TutorBench non-calculus/Eedi/MathDial to held-out calculus cases.
- The live per-student A/B is descriptive at about 50 students; report fallback use separately.
  Do not infer learning gains from offline scores or small live samples.

Dataset permissions and artifact restrictions stay in decision 0005; OpenStax is retrieval-only.
