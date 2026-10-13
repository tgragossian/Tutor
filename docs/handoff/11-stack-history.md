[Index](../../handoff.md) · [Review](../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 352–377. Review findings remain unresolved.

## 5. Proposed Technology Stack

These are initial preferences, not irreversible commitments.

| Component | Candidate technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React |
| Math input | MathLive |
| Database | SQLite initially, PostgreSQL later |
| Document extraction | Mathpix API |
| Symbolic computation | SymPy |
| Numerical computation | NumPy |
| Embeddings | Sentence Transformers or hosted embeddings API |
| Retrieval | FAISS initially |
| LLM | Pretrained model via API |
| Deployment | AWS |
| Document storage | AWS S3 |
| Testing | pytest |
| Containers | Docker |
| Version control | Git/GitHub |

Choose the simplest viable implementation before introducing additional infrastructure.

Do not introduce Kubernetes, distributed microservices, or heavyweight MLOps tools unless the requirements justify them.

<!-- End preserved source. -->
