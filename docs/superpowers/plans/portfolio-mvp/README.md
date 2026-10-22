# Portfolio delivery plan — option B

[Handoff](../../../../handoff.md) · [Review](../../../reviews/2026-10-13/README.md)

2026-10-22: B tasks 1–16 implemented; application review fixes verified, deployment pending.
B-R4's load-tool crash handling and hours remain. Host sizing stays deferred to C by Thomas.
See the [handoff](../../../../handoff.md).
See [execution status](milestone-b/03-execution-status.md) and [review follow-ups](milestone-b/05-follow-ups.md).

Status: option B selected; [milestone A](milestone-a/README.md) complete and live.
[Milestone B plan](milestone-b/README.md) approved by Thomas; exit awaits review fixes.
[Decision record](../../../decisions/0001-delivery-verifier-attribution.md) takes precedence over draft rules.
Goal: a deployed Calculus I practice tutor with measured verification, citation-based
hints, reproducible retrieval experiments and clear operational limits.

## Scope

- Three topics: basic derivative rules, trigonometric derivatives and chain rule.
- 20–30 human-reviewed problems, with several per topic and misconception examples.
- One practice mode, accounts/attempt history and a textbook-order baseline.
- Numeric, bounded symbolic-expression and multiple-choice answers first.
- One OpenStax Volume 1 subset for both problems and explanation retrieval.
- FastAPI, Jinja forms/fetch, MathLive, SQLite and Docker; small AWS deployment.
- Progressive hints, citations, documented correctness/abstention behavior.

After the core works, restore features in this order:
diagnostic -> exam conditions and recap -> all 15 topics -> extraction pipeline -> LoRA.
See the [expansion queue and gates](05-expansion-queue.md). Nothing in that queue is dropped.
Implicit differentiation is retained for topic expansion using exact polynomial checks.
Add the other answer formats with the topics that require them; estimate expansions separately.
The initial core uses the shared real-domain default, ignoring provably removable holes.

## Planning budget

These are timebox proposals, not measured estimates or promises.

| Milestone | Hours | Deliverable and exit gate |
|---|---:|---|
| [A: contracts and deployed skeleton](01-foundation.md) | 20 | Real input fixtures, reviewed schema, CI and HTTPS skeleton |
| [B: practice loop](02-practice.md) | 30 | Accounts, reviewed problems, bounded verifier, durable attempts, browser demo |
| [C: evaluated RAG hints](03-rag.md) | 40 | Citation-based hints plus retrieval and tutoring comparisons |
| [D: reproducibility and operations](04-release.md) | 25 | Corpus rebuild, cost/latency report, restore and rollback |
| [E: final evaluation and portfolio](04-release.md) | 20 | Frozen benchmark, demo, limitations and reproducible results |
| Contingency | 25 | Integration issues and learning time |
| Total | 160 | Eight weeks at the assumed 20 hours/week |

At each gate record actual hours; adjust delivery dates if a timebox is exceeded.
These core timeboxes do not include the full expansion queue.
Never use an accuracy or resource-containment shortcut to recover schedule.
The original first phase alone could plausibly take 80–120 hours; that is my
engineering estimate, not a benchmark, and depends heavily on content work and familiarity.
Its 15 × (5 recall + 2 concept) requirement adds at least 105 authored items to 20 problems.
Twenty problems also cannot provide two unseen diagnostic problems across all 15 topics.

## Why this ordering fits the resume

The existing fare project already shows modeling and careful evaluation.
This project should add evidence of serving a model-backed product and maintaining it:
an inspectable API, deployment, CI, labeled evaluations, failure analysis and costs.
Fine-tuning is valuable only with a controlled experiment and a defensible result.

For later LoRA: hold the base model, retrieval, prompt and decoding fixed; train only
the adapter, then evaluate on held-out calculus interactions and inspect regressions.
Do not promise learning gains or a better tutor based solely on offline scores.

## Next implementation step

Follow the selected order and [verifier decisions](../../../decisions/0001-delivery-verifier-attribution.md).
Follow the approved [milestone B plan](milestone-b/README.md) and its human gates.
Read the [plan review](../../../reviews/2026-10-15-milestone-b/README.md) before affected tasks.
Thomas selected subagent-driven execution for milestone B.
The original 20 tasks remain linked [here](../2026-10-13-core-practice-loop.md) for reuse.
