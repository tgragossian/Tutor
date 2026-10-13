[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 405–448. Review findings remain unresolved.

## 7. Evaluation Requirements

Evaluation is a priority because this is intended as a rigorous ML engineering project.

Maintain independent evaluation sets and reproducible experiments.

Potential metrics:

**Document ingestion**
- Exercise extraction accuracy
- Equation transcription accuracy
- Exercise/solution matching accuracy

**Answer verification**
- False acceptance rate
- False rejection rate
- Inconclusive verification rate
- Performance across supported problem types

**Retrieval**
- Recall@K
- Mean Reciprocal Rank
- Citation accuracy

**Tutoring**
- Mathematical correctness
- Hint usefulness
- Premature solution disclosure
- Responsiveness to misconceptions

**Recommendations**
- Student performance prediction accuracy
- Ranking quality against expert-labeled cases
- Performance relative to rule-based and static baselines

**System engineering**
- API latency
- Error rates
- LLM API costs
- Document processing costs
- Deployment reliability

Do not claim improved student learning without appropriately designed student testing.

<!-- End preserved source. -->
