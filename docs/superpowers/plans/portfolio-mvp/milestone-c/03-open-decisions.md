# C and LoRA: open decisions register

[Parent milestone C plan](../03-rag.md) · [AI handoff](../06-ai-decisions-handoff.md)

Updated 2026-10-22. This page owns unresolved choices; accepted decisions stay in 0004/0005.
Next step: milestone C design session with Thomas. Documentation sync does not authorize compute.

| ID | Open item | Next evidence or decision |
|---|---|---|
| C-O1 | RunPod serving test | Thomas's account/go-ahead; measure fit, cold/cached starts, latency and bill |
| C-O2 | Training host alternative | AWS remains selected; Thomas may choose RunPod Pods after comparison |
| C-O3 | Lightsail sizing | Measure actual C retrieval memory and revisit the 1 GB exception |
| C-O4 | Automated problem sets | Thomas chooses scope/order for templates or LLM generation; no task assigned yet |
| C-O5 | Hosted access | Thomas supplies OpenAI/Anthropic API access through secrets configuration |
| C-O6 | C design session | Turn the accepted direction into contracts, tasks, limits and acceptance checks |

## Design inputs still needed (C-O6)

- Corpus subset and snapshot provenance; local BM25/index memory and later embedding placement.
- Exact callable model versions, budget/rate/timeout values and comparison margin.
- Help payload/event schema, context bounds and confusion-list choices.
- Leak-guard expression extraction, resource bounds, reveal semantics and safe failure behavior.
- Dataset eligibility (including image-bearing tasks), partition IDs and contamination procedure.
- Live A/B rollout for existing students, event retention and linking hints to next attempts.

These are implementation details to resolve, not reversals of the accepted decisions.
The [help contract](01-help-contract.md) and [evaluation gates](02-evaluation.md) constrain them.

## Dependencies and boundaries

- [Serving test procedure](../../../../decisions/0005-tutoring/01-compute-and-serving.md)
  and [cost assumptions](../../../../decisions/0005-tutoring/02-sizing-and-costs.md) support C-O1/C-O2.
- [Host sizing](../../../../ops/host-sizing.md) owns the B measurements and C-O3 exception.
- [Expansion queue](../05-expansion-queue.md) still includes extraction; automated sets are a
  separate proposed feature until C-O4 is decided. Generated candidates require human review.
- Keep keys out of documentation and git; [security](../../../../ops/security.md) owns secrets guidance.
- B's remaining hours gate stays in [B status](../milestone-b/03-execution-status.md).
  No API call, GPU job, endpoint creation or deployment was performed for this doc sync.
