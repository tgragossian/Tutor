[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 244–278. Review findings remain unresolved.

### 4.4 Retrieval-Augmented Tutoring

RAG will primarily retrieve explanatory mathematical knowledge, not act as the entire problem database.

Use a structured database for problem records, answers, tags, and student attempts.

Use a retrieval index for:

- Definitions
- Theorems
- Explanations
- Worked examples
- Relevant textbook sections

Possible retrieval approaches:

- Dense vector retrieval
- BM25 keyword retrieval
- Hybrid retrieval

Initially compare a simple retrieval baseline against an improved approach.

Preserve citations to source documents, sections, and pages.

The tutor should:

- Explain relevant concepts.
- Offer progressive hints.
- Prefer guiding students over prematurely revealing solutions.
- Respond to the student's specific question or misconception.
- Support full explanations when appropriate.
- Acknowledge uncertainty when mathematical verification is unavailable.

RAG retrieval does not guarantee mathematical correctness.

<!-- End preserved source. -->
