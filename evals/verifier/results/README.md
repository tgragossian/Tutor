# Verifier evaluation results

[Evaluation guide](../README.md) · [Review sheet](../human/REVIEW.md)

## Reviewed milestone B release gate

[dev-b.json](dev-b.json) is the reviewed, non-draft release result, committed in e995438.
Command: `evaluate --set dev --gate B`, tested verifier `0.1.0+b5ad4b2`.
All 136 cases are human-reviewed (`tg`): 49 correct, 50 incorrect, 37 unsupported.

| Measure | Observed | 95% Wilson upper bound for zero events |
|---|---|---|
| False accepts | 0 of 50 | 7.1% |
| False rejects | 0 of 49 | 7.3% |
| Correct-answer coverage | 49 of 49 | — |
| Unsupported graded correct | 0 of 37 | 9.4% |
| Agreement with labels | 136 of 136 | — |
| Internal errors | 0 | — |

Seven cases return `wrong_decimal_places`: d-253-02/03/04/05/06/08/19.
The result records `draft: false`, content version `fbb7917d6658`, and dataset SHA-256
`9a24709cb6f92764fb889e0185259cd8d69eb719c61c045a4da1c71ad4738a65`.
The dataset hash matches the committed `human/dev.jsonl`.
These are reviewed development-set results, not a held-out final evaluation or learning study.
Use this result for resume claims; the old 0/54 denominator no longer describes this set.

## CI evidence

[CI run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416) at d673400
is the first green milestone-b run: Python, Node and container smoke all succeeded.
Thomas reported 722 Linux tests passing, including the memory-limit test skipped on Windows.
Python includes both the generated gate and the reviewed dev gate (enabled in 8a0bb40).
Earlier runs failed on a Linux pool-test teardown error: the test's `psutil.wait()` reaped
an externally killed worker, hiding its exit status from multiprocessing. d673400 fixes
that test cleanup; it does not relax verifier containment or gate thresholds.
Remaining GitHub Node 20/Ubuntu deprecation notices are warnings, not failures.
CI status/test counts above are Thomas's reported run evidence; this docs pass inspected
local commits, workflow and result artifacts, without rerunning Linux CI or live health checks.

## Historical artifacts

[dev-draft.json](dev-draft.json) is the older 131-case unreviewed draft, retained for history.
It reported FA 0/54, FR 2/52, coverage 43/52 and agreement 122/131; it is not release evidence.
The later pre-R24 136-case draft was also superseded by the reviewed result above.
The generated mutation set remains regression-only and is never cited as measured accuracy.
