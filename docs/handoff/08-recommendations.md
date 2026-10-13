[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 279–308. Review findings remain unresolved.

### 4.5 Personalized Problem Recommendations

This should become one of the central ML components.

The system should select problems based on:

- Previously attempted problems
- Correctness history
- Prerequisite knowledge
- Topic mastery estimates
- Estimated difficulty
- Previously viewed hints
- Repeated attempts
- Recent performance

Start with a transparent rule-based recommendation algorithm.

Potential later approaches:

- Bayesian Knowledge Tracing
- Item Response Theory
- Other supervised student-performance models
- Contextual bandits, if sufficient reliable interaction data becomes available

Do not introduce complex ML before establishing baselines and obtaining suitable data.

Measure recommendation and student-performance prediction quality separately from claims about actual learning gains.

A core research question is whether personalized recommendations outperform static textbook order or simpler recommendation policies.

<!-- End preserved source. -->
