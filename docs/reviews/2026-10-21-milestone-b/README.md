# Milestone B code review — 2026-10-21

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [Execution status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)

Reviewed `milestone-b` at d428bd7, with the preceding uncommitted documentation sync retained.
Focus: app-track changes since 102a22f, plus verifier boundaries, content loading and release wiring.
Five findings were reproduced locally. No production-code fixes were made by this review.

## Findings

| ID | Priority | Finding | Detail |
|---|---|---|---|
| B-A1 | P1 | Delayed/duplicate Skip can mutate the next presentation | [State](01-state-and-ui.md#b-a1-p1-bind-actions-to-a-presentation) |
| B-A2 | P2 | Deep JSON below the byte cap returns an unhandled 500 | [Input](02-input-and-storage.md#b-a2-p2-handle-json-parser-depth-before-structural-validation) |
| B-A3 | P2 | SQLite contention in authentication/reads escapes as 500 | [Storage](02-input-and-storage.md#b-a3-p2-map-lock-contention-outside-practice-write-transactions) |
| B-A4 | P2 | Existing presentations silently use new content under an old version | [State](01-state-and-ui.md#b-a4-p2-enforce-the-presentations-content-version) |
| B-A5 | P2 | A late format response can restore a completed item in the UI | [UI](01-state-and-ui.md#b-a5-p2-discard-stale-format-results-and-order-ui-mutations) |

P1: fix before release; P2: correctness/reliability work to resolve before milestone B exit.
Task 16's known missing container migrations/volume is separate, unfinished release work.

## Dispositions

All five fixed in 4eba48f with regression tests: see [dispositions](04-dispositions.md).

## Evidence

- [Validation and reproduction instructions](03-validation.md).
- [Executable review probes](repro_app.py): five assertions of desired behavior fail on d428bd7.
- Existing suite: 839 Python tests passed, one skipped; 19 Node tests passed.
- Lint, source type checks and offline validation of six content problems passed.
- No fresh Linux CI, Docker, production probe or browser execution was performed.

## Claude's next steps

1. Fix B-A1 and B-A5 together: presentation-bound actions and ordered client mutations.
   Update API contracts/examples, service signatures, routes and browser code together.
2. Fix B-A2/B-A3 error handling; cover raw HTTP bodies and authentication dependencies.
3. Choose an explicit version policy for B-A4: immutable snapshots or stale-session rejection.
4. Move the relevant probes into the normal test tree as regression tests, with stronger
   assertions for the chosen behavior; preserve the existing mathematical gates.
5. Rerun focused tests, then full Python/Node/lint/types/content checks. Update this review's
   dispositions with fix commits and observed results; do not erase the original findings.
6. Resume task 15 content/review and task 16 container/host release work.
