# C1 debugging fixes — 2026-10-28

[Review index](README.md) · [Pre-fix recheck](07-recheck.md) · [Debugging tree](../../ops/debugging/c1/README.md)

Changes on `milestone-c1`, based on `b16a206`; not merged or deployed at validation time.
R4/R7 are closed locally; all nine original findings now have verified code fixes.
This page owns the R4/R7 fixes after the documentation recheck. The earlier pages preserve
the failures at the unchanged commit; they are not the status of this working tree.

## C1-R4: claim before scoring

- `help/eval/run.py` rejects `--split holdout --retrieval-only` before loading evaluation
  rows. Free retrieval diagnosis remains available on dev.
- A normal holdout run atomically claims the partition before computing/printing retrieval
  metrics or calling a provider. A rerun on a new commit cannot expose scores before rejection.
- A crash during retrieval leaves the claim consumed. Existing overlap, legacy-marker and
  concurrent-claim protection stays in place; no real claim or holdout result was changed.
- `test_eval_spend_holdout.py` now covers used/unused retrieval-only refusal, claim ordering,
  rejected rescoring, retrieval interruption and dev-only scoring. The existing eight-way
  claim race still admits one runner. A test that copied real holdout files was replaced
  with the synthetic claim-ordering regression.

## C1-R7: carry evaluation mode through judging and reports

- `CaseRecord.no_passages` records the evaluation-only uncited schema. `judge_items`
  chooses that schema only for baseline records; production citation rules stay unchanged.
- Raw blocked baseline replies remain judgeable. Cited R35 classification replies still
  parse; the baseline deliberately writes at the labeled level without classifying.
- Mode survives JSON round trips. Older artifacts recover it from run metadata's
  `no_retrieval` flag, so recompute does not silently drop their uncited output.
- Baseline replies reach blind judge/audit rows and human overrides affect paired metrics.
  Citation support has no applicable denominator for this arm and displays N/A. The
  baseline remains diagnostic and cannot qualify a model for production release.
- Tests cover ordinary/feedback baselines, classification, invalid/malformed output,
  blocked raw math, round trips, legacy load, audit/recompute and paired human labels.

## Validation

- Focused evaluation suite: 56 passed.
- Saved R4/R7 reproductions: 2 passed without xfail markers.
- Ruff lint/format and mypy: passed (64 source files type-checked).
- Full Python suite: **1,645 passed, 3 skipped**, 298.98 s; no failures.
- Node suite: 48 passed. Content check: all 22 problems OK.
- Verifier gate B: generated agreement 94/94, FA 0/84, FR 0/10; dev agreement 136/136,
  FA 0/50, FR 0/49. Both gates passed.
- Documentation/link checks passed in root, C1 and C2; all Markdown remains at most
  100 lines. `git diff --check` and changed/new Markdown whitespace checks passed.

Commands: `python -m pytest -q --tb=short`, `npm test --prefix tools`,
`python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy src`,
`python -m mathtutor.verify.content_check`, `python -m mathtutor.verify.evaluate --set generated --gate B`
and `--set dev --gate B`, `python tools/check_docs.py`, `git diff --check`.
Python commands used the worktree's `.venv/Scripts/python.exe`.

The API-key environment variable is removed from test commands. Tests use scripted providers
and temporary synthetic claims. No paid inference, actual holdout campaign or deployment ran.

## Probe cleanup and next step

The original Python/UI review probes are retired navigation stubs; their historical
implementations remain in git at `b16a206`. Passing regressions live in the normal test tree.
The two follow-up probes remain executable and passing; no fixed finding retains an xfail/TODO.

After local checks, follow the [owner release gates](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md).
Container smoke/memory, provider evidence, case/copy review and release holdout remain separate.
C2 still needs these local fixes carried to its branch and its plan reviewed before implementation.
