# AI decisions handoff: C and LoRA

[Plan index](README.md) · [Main handoff](../../../../handoff.md) · [C design entry](03-rag.md)

Source: Thomas's 2026-10-22 decisions, collected on `milestone-b` in commit `3284327`.
Synced into the main checkout on 2026-10-22. This is a navigation/sync record, not a second
decision authority. [0004](../../../decisions/0004-rag-source-models-and-evaluation.md) and
[0005](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md), including its children,
own accepted decisions. Implementation has not started; next is the C design session.
Thomas's recorded OpenStax/TutorBench licensing choices and revisit conditions are preserved.

## Decided: where each item lives

| # | Decision | Owning document |
|---|---|---|
| 1 | C → LoRA → D/E → expansion | [0005 §6](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md#6-timing-compute-and-serving-thomas-2026-10-22) |
| 2 | OpenStax retrieval with section links/licence | [0004 §1](../../../decisions/0004-rag-source-models-and-evaluation.md#1-openstax-text-in-retrieval) |
| 3 | BM25 first; measured dense/hybrid comparison | [C evaluation](milestone-c/02-evaluation.md) |
| 4 | GPT-5.2 baseline vs Claude 5.5 candidates; Muse Spark dropped | [0004 §2](../../../decisions/0004-rag-source-models-and-evaluation.md#2-generator-candidates) |
| 5 | Hint behavior, not student-answer grading; Wilson intervals | [C evaluation](milestone-c/02-evaluation.md) |
| 6 | Three help buttons and server-owned context | [Help contract](milestone-c/01-help-contract.md) |
| 7 | Bounded SymPy answer-leak guard below reveal | [Help contract](milestone-c/01-help-contract.md) |
| 8 | TutorBench non-calculus/Eedi/MathDial train; Calculus/TutorMoments/C eval | [0005 §§1–2, 4](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md) |
| 9 | Qwen3.5-9B, QLoRA, one adapter; Qwen-generated training responses | [0005 §§3–4](../../../decisions/0005-tutoring-datasets-and-fine-tuning.md) |
| 10 | Paired base/LoRA headline A/B; LoRA/hosted reference A/B | [C/LoRA evaluation](milestone-c/02-evaluation.md) |
| 11 | AWS GPU training; quota/budget preparation; stop between runs | [Compute/serving](../../../decisions/0005-tutoring/01-compute-and-serving.md) |
| 12 | RunPod Serverless, one 24 GB worker, scale to zero | [Compute/serving](../../../decisions/0005-tutoring/01-compute-and-serving.md) |
| 13 | Persistent per-student live A/B; descriptive at about 50 students | [Compute/serving](../../../decisions/0005-tutoring/01-compute-and-serving.md) |
| 14 | Assigned base/LoRA → hosted → unavailable; practice continues | [Help contract](milestone-c/01-help-contract.md) |

## Sizing and costs

[Sizing/cost supplement](../../../decisions/0005-tutoring/02-sizing-and-costs.md) owns GPU estimates
and the provisional $2/month versus $5–8/month restart scenarios. It records the unresolved
$0.92 calculator versus $0.69/hour rate mismatch. These are not observed bills or verified fit.

## Open

[Open decisions register](milestone-c/03-open-decisions.md) owns the RunPod serving test,
AWS versus proposed RunPod training, Lightsail sizing, automated sets, API access and C design.
The serving test still needs Thomas's account/go-ahead. AWS remains the selected training host.

## Doc updates for Codex: completed in this sync

1. Main `handoff.md`: C → LoRA order, correct model shortlist and link here; stale claims removed.
2. Decision 0005 §3: Muse Spark removed from active comparison candidates.
3. Decision 0005 §6: split compute/serving and sizing/costs into linked children; test remains open.
4. [03-rag](03-rag.md): buttons, context, leak guard, fallback and event requirements; linked children.
5. [04-release](04-release.md): Qwen/dataset transfer, AWS/RunPod, offline and live A/B.
6. [Expansion queue](05-expansion-queue.md): extraction stands alone; no “LoRA after extraction”.
7. [Plan index](README.md) and [host sizing](../../../ops/host-sizing.md): linked and synchronized.
8. [Original scope](../../specs/core-practice-loop/00-scope.md): preserved as historical reference.

Current status pages also reflect Thomas's recorded B deploy at 8057590 with migration 0003.
Dated review evidence is retained; no new application, browser, host or GPU validation is implied.
