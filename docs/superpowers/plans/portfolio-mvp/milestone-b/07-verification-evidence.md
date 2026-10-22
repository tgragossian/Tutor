# Milestone B: verification evidence

[Milestone B plan](README.md) · [Execution status](03-execution-status.md)

Updated 2026-10-22. Fresh local checks and earlier/owner-reported runs are separated below.

Latest: [fix recheck at f3a4e40](../../../../reviews/2026-10-22-milestone-b/07-recheck.md):
904 Python passed/3 platform skips, 26 Node passed; original probes and populated 0002→0003
upgrade pass. Both recovery departures accepted. B-R4's verifier-crash case: fixed in
04de2d2; all recheck probes pass. Browser/CI claims in dispositions were not independently rerun here.

## Fresh whole-branch review at 15169a2

Source: [2026-10-22 validation](../../../../reviews/2026-10-22-milestone-b/04-validation.md).

- Windows: 890 Python passed/one Linux-only skip, 19 Node passed; lint/format/types passed.
  All 22 content problems passed; recompilation was byte-identical.
- Dev CLI: FA 0/50, FR 0/49, coverage 49/49, agreement 136/136; generated CLI: FA 0/84,
  FR 0/10, coverage 10/10, agreement 94/94. No internal errors; both B gates pass.
- Local version `0.1.0+dev`; published SHA-tagged artifacts unchanged. Four Python and one
  JavaScript probes failed on [five new findings](../../../../reviews/2026-10-22-milestone-b/README.md);
  after ca54407 all pass ([dispositions](../../../../reviews/2026-10-22-milestone-b/06-dispositions.md)).
- Prior B-A1–B-A5 regressions pass. No fresh browser, Docker, remote CI, Linux/host run.

## Recorded release evidence (2026-10-22)

- Thomas approved all 22 problems (3c0141c). The handoff records deployment at 9bf6b29,
  `/readyz` 22, migrations 0001–0002, and green CI run 39828899000; not queried in this review.
- 375ab7c adds worker settings, disables duplicate access logs and runs browser e2e against
  the image via `tests/container/smoke.sh`. The workflow/wiring was inspected locally.
- [Host sizing](../../../../ops/host-sizing.md): 8 incorrect grades, 8 verifier_busy replies;
  peak app container 185.2 MiB, minimum available 281 MiB. Thomas deferred sizing to C,
  retaining 1 GB / one worker / 384 MB as an exception. B-R4 does not invalidate this record.
- [Verifier guide](../../../../verifier/README.md) and [results](../../../../../evals/verifier/results/dev-b.md)
  are published. Review fixes and actual hours remain before B closure.

## Historical app track: tasks 10–15 at d428bd7

Source: d428bd7's handoff/status and implementation commits d865179..5fd8952.

- Tasks 10–14: the handoff reports 839 Python tests and 19 Node tests passing.
- Task 12: the execution status reports the submission-race tests passed three times.
- Task 14: a real browser typed `18x(3x^2+1)^2`, received "Correct", and showed no CSP
  violations. The CSP change and SRI checks are in [security](../../../../ops/security.md).
- Task 15: 5fd8952 adds `tools/e2e/smoke.mjs` and the `e2e` CI job. CI starts a migrated
  SQLite app under uvicorn; container execution was added later in task 16.
- The handoff does not separately record a complete scripted e2e result or a remote
  CI pass for 5fd8952. Keep those gates distinct from the manual browser check.
- At this snapshot six problems were reviewed; expansion/review subsequently completed.

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
- These runs predate tasks 10–14; later release evidence is above.
- Recorded live probes on 2026-10-20: `/healthz` 200, `/readyz` 200; milestone A host.
- Current ownership/checks: [release debugging](../../../../ops/debugging/02-release.md).

## Later code review (2026-10-21)

[Fresh validation](../../../../reviews/2026-10-21-milestone-b/03-validation.md): 839 Python passed,
1 skipped; 19 Node passed; lint, source types and content check passed. Five isolated review
probes fail on d428bd7; [findings](../../../../reviews/2026-10-21-milestone-b/04-dispositions.md)
were subsequently fixed in 4eba48f (author reports 851 Python/19 Node and local browser passes).
No fresh browser, Docker, Linux CI/memory or live-host evidence was collected.

## Earlier documentation sync

Inspected local commits, implementation, tests, workflow and existing result artifacts.
Validation uses `tools/check_docs.py` for line counts and local links, plus `git diff --check`.
No application tests, remote CI, host memory measurement or live probes were rerun.
