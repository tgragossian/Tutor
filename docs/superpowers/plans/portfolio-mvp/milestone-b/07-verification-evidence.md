# Milestone B: verification evidence

[Milestone B plan](README.md) · [Execution status](03-execution-status.md)

Updated 2026-10-21. Recorded results below are not fresh test executions by this docs pass.

## App track: tasks 10–15

Source: d428bd7's handoff/status and implementation commits d865179..5fd8952.

- Tasks 10–14: the handoff reports 839 Python tests and 19 Node tests passing.
- Task 12: the execution status reports the submission-race tests passed three times.
- Task 14: a real browser typed `18x(3x^2+1)^2`, received "Correct", and showed no CSP
  violations. The CSP change and SRI checks are in [security](../../../../ops/security.md).
- Task 15: 5fd8952 adds `tools/e2e/smoke.mjs` and the `e2e` CI job. CI starts a migrated
  SQLite app under uvicorn; container execution remains task 16.
- The handoff does not separately record a complete scripted e2e result or a remote
  CI pass for 5fd8952. Keep those gates distinct from the manual browser check.
- Task 15 content remains six reviewed problems; 14–24 additions and review are pending.

## Reviewed verifier gate: tasks 1–9

- Source/captures at b5ad4b2 match: 136 reviewed (`tg`), 49 correct, 50 incorrect,
  37 unsupported; `d-sqsq-02` includes zero, `[0, inf)`.
- [dev-b.json](../../../../../evals/verifier/results/dev-b.json), committed in e995438,
  records `evaluate --set dev --gate B` without `--draft` at verifier `0.1.0+b5ad4b2`.
- FA 0/50 (95% Wilson upper bound 7.1%), FR 0/49 (7.3%), coverage 49/49;
  unsupported accepted 0/37 (9.4%), agreement 136/136, no internal errors.
- Seven R24 cases return `wrong_decimal_places`. Problem 253 permits an exact answer
  or rounding to three places. [R24 checklist](r24/README.md) owns precision debugging.
- [Results index](../../../../../evals/verifier/results/README.md) owns artifact provenance;
  `dev-draft.json` is historical. These are dev results, not the held-out final evaluation.

## Historical CI and production evidence

- 8a0bb40 enables the reviewed dev gate alongside the generated regression gate.
- [Run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416), d673400:
  Python, Node and container smoke passed. Thomas reported 722 Linux tests, including
  the Linux memory-limit test. The pool-test teardown fix did not relax containment.
- [Run 39506433419](https://github.com/tgragossian/Tutor/actions/runs/39506433419), main merge
  102a22f: the prior handoff records Python, Node and container smoke passing.
- These runs predate tasks 10–14. They do not establish current branch container readiness.
- Last recorded live probes, 2026-10-20: `/healthz` 200, `/readyz` 200; milestone A host.
- Task 16 still needs migrations/storage, measured Linux memory under 16 concurrent
  submissions and deployed browser evidence. [Release debugging](../../../../ops/debugging/02-release.md).

## Later code review (2026-10-21)

[Fresh validation](../../../../reviews/2026-10-21-milestone-b/03-validation.md): 839 Python passed,
1 skipped; 19 Node passed; lint, source types and content check passed. Five isolated review
probes fail on d428bd7; [findings](../../../../reviews/2026-10-21-milestone-b/README.md) are open.
No fresh browser, Docker, Linux CI/memory or live-host evidence was collected.

## Earlier documentation sync

Inspected local commits, implementation, tests, workflow and existing result artifacts.
Validation uses `tools/check_docs.py` for line counts and local links, plus `git diff --check`.
No application tests, remote CI, host memory measurement or live probes were rerun.
