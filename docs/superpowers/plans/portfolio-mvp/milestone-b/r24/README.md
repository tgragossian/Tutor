# R24: numeric precision and task 9 release

[Milestone B plan](../README.md) · [Execution status](../03-execution-status.md) · [Task 9](../tasks/09-dev-cases.md)

**2026-10-20:** implemented in a76985d with failing tests first. Reviewed captures, gate B
and CI pass; task 9 is complete. Thomas's merge of tasks 1–9 to `main` remains next.

## Scope

Only numeric problems explicitly requesting N decimal places require exactly N places on
standalone decimals. Exact expressions remain allowed; other lengths produce
`wrong_decimal_places` and are not graded. No universal cap applies inside expressions.
Coefficients and fractions stay exact. Removable-hole behavior follows decision 0001.
See the [R24 spec](../../../../specs/2026-10-20-decimal-places-design.md).

## Modules

1. [Pre-check and regressions](01-precheck.md): implementation ownership and debugging.
2. [Content, capture and release](02-release.md): completed checks and remaining merge steps.
3. [Result evidence](../../../../../../evals/verifier/results/README.md): metrics, CI and historical artifacts.

## Completion evidence

- [x] Tests failed before a76985d and passed after implementation.
- [x] Problem 253 wording and compiled content updated in a76985d.
- [x] b5ad4b2 recaptured 136 `tg` cases matching source, including `[0, inf)` for `d-sqsq-02`.
- [x] Non-draft gate B passed: FA 0/50 (95% upper bound 7.1%), FR 0/49, coverage 49/49,
  unsupported accepts 0/37, agreement 136/136; e995438 records `dev-b.json`.
- [x] 8a0bb40 enables the dev CI gate; run 39504828416 is green after d673400's test fix.
- [x] Status/docs report reviewed results; `dev-draft.json` is explicitly historical.
- [ ] Thomas merges tasks 1–9 to `main`, preserving milestone-b's handoff, then checks live health.

Tasks 10–16 remain unfinished. Preserve reviewed labels, FA 0 and containment.
