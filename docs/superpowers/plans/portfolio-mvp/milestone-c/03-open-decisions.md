# C and LoRA: open decisions register

[Parent milestone C plan](../03-rag.md) · [AI handoff](../06-ai-decisions-handoff.md)

Updated 2026-10-26. This page owns unresolved choices; accepted decisions stay in 0004/0005.
Codex's [concept review](../../../../reviews/2026-10-26-milestone-c/README.md) is complete;
the [C design spec](../../../specs/2026-10-26-milestone-c/README.md) includes review amendments.
The [C1 plan](c1/README.md) proposes C-P1 ([pinned values](c1/01-pinned-values.md)) and C-P2
([gates](c1/02-gates.md)) for Thomas's review. No C code exists yet.

| ID | Open item | Next evidence or decision |
|---|---|---|
| C-O1 | RunPod serving test | Thomas's account/go-ahead; measure fit, cold/cached starts, latency and bill |
| C-O2 | Training host alternative | AWS remains selected; Thomas may choose RunPod Pods after comparison |
| C-O3 | Lightsail sizing | Measure C1 retrieval memory; Thomas allows 2 GB if needed (2026-10-26) |
| C-O4 | Automated problem sets | All of Calc 1 only if automated (Thomas, 2026-10-26); **placed after the LoRA** (Thomas, 2026-10-26); position relative to D/E set when the LoRA ends |
| C-O5 | Hosted access | Thomas supplies an Anthropic API key through secrets configuration (no OpenAI, 2026-10-26) |
| C-O6 | C design session | Complete 2026-10-26; Codex review incorporated; implementation plan still needed |

## Implementation prerequisites from review (not new owner decisions)

| ID | Before | Required resolution |
|---|---|---|
| C-P1 | C1 implementation/evaluation | Pin runtime parser/worker interfaces, context/token/candidate bounds, admission limits, misconception schema, tariff/model settings and durable ledger recovery |
| C-P2 | Paid C comparison/public release | Pin primary selection measure, 10-point rule/tolerances, numeric safety/usefulness/citation/retrieval gates, query split and disjoint C/LoRA/E partitions |
| C-P3 | C3 implementation | Pin typed task/domain admission, owned help/practice targets, upload conversion/pixel/page/problem/token bounds, deadlines, transient expiry and deletion/backup/provider retention |
| C-P4 | LoRA experimentation | Dataset eligibility/overlap, untouched final IDs, existing-account assignment and live retention/metrics |

Resolved design direction: whole-book corpus, top 6 BM25, three buttons → C2 text → C3 intake,
30/hour and 150/day help, 10/day uploads, initial $15 monthly admission budget, custom chunk IDs,
Reveal-only intentional answer path, fail-closed recognized math. See exact spec for limitations.
The 15 s total deadline, two-call maximum and typed derivative subset are review amendments;
measure feasibility in implementation, without silently relaxing containment or leakage reporting.
C-O6 stays complete; C-P entries describe remaining implementation choices.

## Dependencies and boundaries

- [Serving test procedure](../../../../decisions/0005-tutoring/01-compute-and-serving.md)
  and [cost assumptions](../../../../decisions/0005-tutoring/02-sizing-and-costs.md) support C-O1/C-O2.
- [Host sizing](../../../../ops/host-sizing.md) owns the B measurements and C-O3 exception.
- [Expansion queue](../05-expansion-queue.md) still includes extraction; automated sets are a
  separate feature placed after the LoRA (C-O4). Generated candidates require human review.
- Keep keys out of documentation and git; [security](../../../../ops/security.md) owns secrets guidance.
- B is closed; Thomas removed the hours gate on 2026-10-26. [B status](../milestone-b/03-execution-status.md).
  No API call, GPU job, endpoint creation or deployment was performed for this doc sync.
