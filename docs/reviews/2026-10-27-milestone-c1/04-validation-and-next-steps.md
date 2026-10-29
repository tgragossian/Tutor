# C1 review: original validation and fix checklist

[Review index](README.md) · [Current recheck](07-recheck.md) · [Fresh validation](10-recheck-validation.md)

Historical evidence at `3be5808`; the recheck links above supersede the open status and
fix-order checklist below. Preserve these results separately from later verification.

Reviewed 2026-10-27, `milestone-c1` HEAD `3be5808`, base `main` `292cee4`.
Scope: parser/guard, corpus ingestion/retrieval, state/privacy/accounting, provider/pipeline,
API/UI, migrations, evaluation/selection and deployment changes. Findings are open, not fixes.
The corpus artifact was checked through its loader/hash/tests; this was not a human audit
of every textbook passage or every converted equation.

## Fresh local evidence

| Check | Result |
|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | 1561 passed, 3 skipped; 237.03 s |
| `npm test --prefix tools` | 41 passed |
| Ruff lint / format, `mypy src` | Passed; 61 source files type-checked |
| `python -m mathtutor.verify.content_check` | 22 problems OK |
| Verifier generated `--gate B` | Passed: 94/94 agreement, FA 0/84, FR 0/10 |
| Verifier dev `--gate B` | Passed: 136/136 agreement, FA 0/50, FR 0/49 |
| Review Python probes | 11 expected failures across eight findings |
| Review UI probe | One TODO assertion reproduces C1-R8 (`uuid-2` versus `uuid-1`) |
| Documentation checks | Relative links resolve; all Markdown files stay at most 100 lines |

The initial sandbox pytest run failed to access its temporary directory. The approved
rerun above passed. Those setup errors were not counted as application defects.
Expected-failure probes are separate from the default test suite; they are not passing
regressions. Running with `--runxfail` confirmed all eleven fail at their intended assertions.

```powershell
.venv\Scripts\python.exe -m pytest docs/reviews/2026-10-27-milestone-c1/test_review_probes.py -q -rx
.venv\Scripts\python.exe -m pytest docs/reviews/2026-10-27-milestone-c1/test_review_probes.py -q --runxfail --tb=short
node --test docs/reviews/2026-10-27-milestone-c1/review_ui_probe.mjs
.venv\Scripts\python.exe tools/check_docs.py
```

## Claude fix order and closure

1. Fix C1-R1/R2/R3/R9 before enabling help or paying for evaluation. Include container packaging,
   fail-closed foreign math, dispatch-aware accounting and interrupted-run recovery regressions.
2. Fix C1-R4 before any actual holdout. Use synthetic partitions/markers for development;
   never consume the real release set to test its one-shot enforcement.
3. Fix C1-R5/R6/R8 before building C2 on these contracts. Resolve C1-R7's ablation semantics
   explicitly; do not call an always-abstaining control a model comparison.
4. Move desired assertions into normal tests and remove xfail/TODO as each issue is fixed.
   The packaging probe deliberately models the old layout; replace it with a real image test.
5. Add a linked disposition page here with each ID, fixing commit, regression test and evidence.
   Update this index, the C1 status and `handoff.md`; do not mark unresolved items complete.
6. Rerun focused regressions, the normal suites and repository CI checks. Then resume the
   owner release checklist in [C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md).

## Evidence still required

- Docker is unavailable locally: no production-image build, container e2e or memory gate.
- No paid calls, key access, live-provider compatibility check, actual holdout or deployment.
- Owner review of labels/cases/copy and the previously disclosed retrieval scores still stand.
  This review neither changes numeric release gates nor grants a fresh-holdout claim.
- Public provider pricing/API documentation was not revalidated in this local code review.
  Local fake-provider success is not evidence of real endpoint behavior or actual spend.
