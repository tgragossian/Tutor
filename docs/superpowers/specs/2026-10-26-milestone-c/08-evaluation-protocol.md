# C design 8: partitions, scoring and selection protocol

[C design](README.md) · [Acceptance](05-evaluation-and-acceptance.md) · [Review rationale](../../../reviews/2026-10-26-milestone-c/04-evaluation.md)

Review amendment, 2026-10-26. C-P2 owns unresolved numerical gates; no evaluation has run.

## Partitions and timing

- Prepare 60 reviewed help cases: 36 development, 24 frozen C release holdout. Group by source
  problem AND family/template before splitting; all hint levels and attempts stay together.
  Track exact IDs/hashes and overlaps. Twenty-two bank items are not sixty independent problems.
- C1 cases cover the bank's three topics/help types; C2/C3 need additional targeted release
  cases for routing, broader book questions and intake. Do not imply C1 validates the whole book.
- The C holdout runs after C selection and before C release. After publication it becomes a
  regression set, excluded from LoRA training/selection but no longer an untouched final test.
- Reserve a separate disjoint LoRA/E final partition before experimentation. E runs a locked
  paired comparison of predeclared models/arms. Do not inspect final labels to choose adapters.
- Fixes based on holdout failures convert those cases to regression evidence. Record every run;
  fresh held-out cases are needed for a renewed independent performance claim.
- Partition the 40 retrieval queries before tuning; label relevant chunks against a frozen
  corpus. Choose the development/holdout allocation in C-P2. Cover chapters and notation types.

## Metrics and denominators

Score both raw generations and the final delivered experience, including abstentions and
safe-message fallback. Report counts by help type, level, topic and guarded/hints-only mode.

| Metric | Denominator / interpretation |
|---|---|
| Leakage | All eligible requests; also conditional on shown hints and across L1→L3 episodes |
| Error-specific help | Cases with a known wrong attempt/misconception, not generic explanations |
| Wrong-reasoning endorsement | Cases containing mistaken reasoning |
| Citation support | Delivered substantive responses; audit each cited claim against chunks |
| Useful coverage | Eligible in-scope requests receiving a useful substantive response |
| Appropriate abstention | Separate out-of-scope/insufficient-context and answerable cases |
| Math errors | Raw and delivered substantive responses, with counts |
| Retrieval Recall@6/MRR@6 | Queries with relevant chunks; no-relevance negatives reported separately |
| Cost/latency | All requests including failed/blocked/retried ones; cost per useful hint too |

An always-abstaining system must fail useful coverage even if its leakage is zero.
Track invalid JSON/citations, parser rejection, false blocks, timeout and fallback rates.
Wilson intervals apply to marginal proportions; use paired outcome tables and family-grouped
uncertainty for model differences. Report low sample size; do not infer learning gains.

## Judging and model selection

- Blind model identity and randomize order for judging. Version the rubric/judge config;
  include authoritative case answers and source chunks in offline judging only.
- Thomas's random 20% check is stratified by help type/topic; additionally review all flagged
  leakage/endorsement and disagreements. Separate random agreement from targeted adjudication.
- Haiku is the default candidate; a 10-percentage-point gain is the proposed practical
  threshold. Predeclare the primary measure and safety/coverage constraints in C-P2.
  Reject “better on either metric” when the other regresses beyond its preset tolerance.
- If neither passes release gates, neither ships. A null/unclear comparison keeps the simpler
  eligible system. This small comparison is not a formal non-inferiority or superiority trial.
- Compare models under fixed retrieval, prompt content, output schema and limits. Record each
  provider's decoding/structured-output differences; identical schema does not mean identical
  sampling semantics. Later Qwen base/LoRA must share the same inference implementation.
- Compare no retrieval/BM25 with one fixed generator on development data. A dense/hybrid
  challenger is optional in C1; retain BM25 unless a controlled comparison justifies complexity.

## C3 reading evidence

Review about 20 problems from 3–4 sheets, including ambiguous notation and unsupported tasks.
Check operation, variable, derivative order, domain/constraints and problem boundaries against
human transcription; equivalence alone cannot detect omitted conditions or a wrong task.
Report transcription success, confirmation corrections, gradable admission and end-to-end
success separately. Split by sheet/family if tuning; do not call twenty related crops independent.
