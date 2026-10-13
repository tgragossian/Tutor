[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 491–556. Review findings remain unresolved.

## 10. Development Priorities

Recommended implementation order:

### Phase 1 — Foundation

- Choose repository structure.
- Establish Python backend.
- Define problem and student-attempt schemas.
- Set up pytest.
- Create a small manually validated problem fixture.

### Phase 2 — Mathematical Verification

- Implement numerical answer checking.
- Implement supported symbolic checks.
- Test edge cases and invalid inputs.
- Provide explicit inconclusive outcomes.

### Phase 3 — Document Ingestion

- Test Mathpix on representative textbook and exam pages.
- Assess mathematical transcription accuracy.
- Parse exercises and source metadata.
- Store structured records.
- Create an inspection/validation workflow.

### Phase 4 — RAG Tutoring

- Chunk explanatory textbook content.
- Build embeddings and a retrieval index.
- Add citation-aware tutoring responses.
- Implement progressive hints.
- Evaluate retrieval quality.

### Phase 5 — Frontend

- Build problem selection UI.
- Integrate MathLive.
- Implement answer submission.
- Display verification feedback and tutoring hints.

### Phase 6 — Personalization

- Implement student attempt history.
- Add topic mastery estimates.
- Establish a static recommendation baseline.
- Implement a simple adaptive recommendation policy.
- Develop an evaluation framework.

### Phase 7 — Cloud Deployment

- Containerize the backend.
- Deploy through AWS.
- Configure storage and credentials.
- Measure costs, latency, and operational reliability.

### Phase 8 — Advanced ML

Only after working baseline infrastructure:

- Evaluate knowledge tracing approaches.
- Compare recommendation algorithms.
- Investigate tutoring fine-tuning.
- Expand to additional mathematics courses.

<!-- End preserved source. -->
