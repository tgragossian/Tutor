# R24: numeric precision and task 9 release

[Milestone B plan](../README.md) · [Execution status](../03-execution-status.md) · [Task 9](../tasks/09-dev-cases.md)

**2026-10-20:** approved, not implemented. Thomas's source review is complete (9b2e1f2).
This checklist implements the [R24 spec](../../../../specs/2026-10-20-decimal-places-design.md).

## Scope

Only numeric problems explicitly requesting N decimal places enforce exactly N places on
standalone decimals. Exact expressions remain allowed. Other decimal lengths produce
`wrong_decimal_places` and are not graded. There is no universal cap inside expressions.
Do not round coefficients or replace exact fractions with decimal approximations.
Removable-hole behavior remains unchanged under decision 0001.

## Modules and order

1. [Pre-check and regression tests](01-precheck.md): original input, place counting,
   mismatch abstention, evaluator agreement and debugging by layer.
2. [Content, capture and release](02-release.md): reviewed source/capture consistency,
   required checks, non-draft gate, CI and merge readiness.

## Starting state

- `dev.src.yaml`: 136 `tg`; 49 correct, 50 incorrect, 37 unsupported.
- `dev.jsonl`: pre-R24 labels and pending markers; not release-ready.
- `d-sqsq-02` now includes zero, `[0, inf)`, in reviewed source; recapture it too.
- No reviewed R24 metrics exist. Preserve historical results as dated evidence.
- Keep FA 0 and containment unchanged. Never change labels to fit verifier output.

## Completion evidence

- [ ] R24 tests fail before implementation and pass afterward.
- [ ] Problem wording, compiled content and reviewed captures agree.
- [ ] Required checks and `evaluate --set dev --gate B` pass without `--draft`.
- [ ] CI enforces the dev gate; results identify tested code/content/dataset versions.
- [ ] Task 9 status and resume metrics reflect the actual reviewed run.
- [ ] Tasks 1–9 are merged to `main` after checks; tasks 10–16 remain unfinished.
