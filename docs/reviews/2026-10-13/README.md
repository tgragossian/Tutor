# Core practice loop review — 2026-10-13

[Documentation](../../README.md) · [Active delivery plan](../../superpowers/plans/portfolio-mvp/README.md)

Recommendation: keep the monolith and evaluation emphasis, revise the verifier and
session contracts, and reduce the first release before executing the task plan.
This is a design review, not a report of observed runtime bugs.

## Findings, ordered by implementation risk

| Priority | Finding | Original location | Details |
|---|---|---|---|
| P1 | Sample agreement is treated as mathematical correctness | Spec §4.2; Tasks 4–6 | [Verifier V1–V3](verifier.md) |
| P1 | Resource and input bounds leave expensive-expression paths open | Spec §4.1/4.4; Tasks 3/7 | [Verifier V4](verifier.md) |
| P1 | Retries and repeated presentations lack a durable identity | Spec §5; Tasks 12/14/16 | [Contracts C1–C3](contracts.md) |
| P1 | Current MathLive releases invalidate the capture API and age rule | Task 2 | [Contracts C4](contracts.md) |
| P1 | Evaluation labels and CI gates do not support the stated claims | Task 10 | [Evaluation E1–E3](evaluation.md) |
| P1 | The first phase consumes too much of the shipping/RAG budget | Spec §1/3.4; Task 9 | [Scope](../../superpowers/plans/portfolio-mvp/README.md) |
| P2 | Parser/UI contracts disagree about decimals, constants and choice input | Tasks 3/5/8 | [Verifier V5](verifier.md) |
| P2 | Deployment sizing, restore testing and release identity need definition | Tasks 19–20 | [Operations](operations.md) |

P1 means resolve before implementing the affected component; P2 means resolve before
the relevant release. These are priorities for a draft, not incident severity labels.

## What is already strong

- A single FastAPI app, server-rendered UI and SQLite fit a small pilot.
- Pure verification and recommendation code is easy to test and explain.
- Curated questions, provenance and three verdict states fit the tutoring use case.
- Attempt history, a static recommendation baseline and explicit evaluation are useful.
- No need for Kubernetes, microservices or a vector database service at this scale.

## Read by concern

- [Verifier correctness and input safety](verifier.md).
- [Session, UI and API contracts](contracts.md).
- [Evaluation and portfolio evidence](evaluation.md).
- [Project structure and dependency boundaries](structure.md).
- [Deployment and operating costs](operations.md).
- [Reference plan](../../superpowers/plans/2026-10-13-core-practice-loop.md).

The three original Markdown documents are preserved as ordered modules.
Their [preservation manifest](archive-manifest.json) records hashes and original line ranges.
Original paths remain entry points. Thomas selected option B after this review.
The [decision record](../../decisions/0001-delivery-verifier-attribution.md) updates scope,
domain semantics, implicit checking and attribution; other findings still need resolution.
The manifest records the explicit amendment to the original commit-attribution rule.

## Initial restructure verification

- 80 Markdown files checked; maximum length 93 lines.
- All local Markdown links resolve; fenced code blocks are balanced.
- All three original documents reconstruct exactly after CRLF/LF normalization.
- Preservation hashes match the manifest; git diff --check passes.
- This was documentation review only; no application tests or experiments were run.
