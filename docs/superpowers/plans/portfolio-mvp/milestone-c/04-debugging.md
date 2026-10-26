# C and LoRA: planned debugging paths

[Parent milestone C plan](../03-rag.md) · [Operations debugging tree](../../../../ops/debugging/README.md)

Design checklist, not a description of implemented modules. Add real file/test paths when
C's implementation plan exists; do not invent commands or report these checks as passing.

| Symptom | Inspect first | Evidence to retain |
|---|---|---|
| Irrelevant passage | Snapshot → chunk IDs → query → BM25 ranking | Relevance labels, top-k IDs, Recall@k/MRR |
| Missing/broken citation | Source-ID validation → metadata → section anchor | Corpus hash, cited IDs and resolved URLs |
| Generic or wrong help | Button → help type → bounded context → prompt | Help type, level, problem/version, matched misconception |
| Answer exposed | Expression extraction → bounded equivalence → response guard | Leak event, supported/unsupported form, human leakage score |
| Slow or unavailable hint | Queue → provider → timeout → fallback | Latency, actual model, fallback reason, usage |
| Wrong A/B attribution | Student assignment → adapter request → serving result | Assigned arm and actual model/adapter separately |
| Unexpected GPU cost | Worker count → idle tail → cold starts → fallback spend | Billable seconds, rate, cache hits and storage charges |
| Web-host memory pressure | Retrieval/index → app/worker → host totals | Same-workload memory burst and C configuration |
| Suspicious evaluation gains | Dataset partitions → overlap check → scoring config | Task IDs, text overlap, versions and per-case paired results |

## Owning documents

- [Help contract](01-help-contract.md): routing, citations, leak guard and failure handling.
- [Evaluation](02-evaluation.md): splits, fixed comparisons, uncertainty and regressions.
- [Compute/serving](../../../../decisions/0005-tutoring/01-compute-and-serving.md): worker limits and A/B fallback.
- [Sizing/costs](../../../../decisions/0005-tutoring/02-sizing-and-costs.md): provisional estimates, not a bill.
- [Open decisions](03-open-decisions.md): unresolved limits, schemas and test prerequisites.
- [B application debugging](../../../../ops/debugging/01-app.md): practice and persisted attempts.
- [Host sizing](../../../../ops/host-sizing.md): measured B baseline and retained exception.

Keep failures reproducible with model/prompt/config and corpus versions. Provider errors or
unparseable output must remain visible; a successful HTTP status alone is not a valid hint.
