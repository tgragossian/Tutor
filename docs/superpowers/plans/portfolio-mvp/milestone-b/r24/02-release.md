# R24: content, capture and release

[R24 checklist](README.md) · [Pre-check](01-precheck.md) · [Result evidence](../../../../../../evals/verifier/results/README.md)

**Completed 2026-10-20:** task 9 release gate and CI pass. Merge/live checks remain Thomas's next step.

## Completed content and capture

- [x] a76985d updates problem 253: “Give an exact answer or round to 3 decimal places.”
  Its compiled content is regenerated; it is the current numeric seed with decimal precision.
- [x] b5ad4b2 recaptures reviewed YAML through MathLive: 136 `tg`, 49 correct, 50 incorrect,
  37 unsupported; source/capture IDs, labels, reviewers, rationales and domains agree.
- [x] `d-sqsq-02` includes zero. `d-253-02` keeps `-0.5830` in both authored and field LaTeX,
  while MathJSON loses the zero. R24 counts the preserved field LaTeX.
- [x] Review sheets reflect the measured release outcomes, including all seven format issues.

## Reviewed gate

[dev-b.json](../../../../../../evals/verifier/results/dev-b.json), committed in e995438,
records this command at tested verifier `0.1.0+b5ad4b2`, with `draft: false`:

```text
uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev-b.json
```

- [x] FA 0/50 (95% upper bound 7.1%); FR 0/49 (7.3%); coverage 49/49.
- [x] Unsupported accepts 0/37 (9.4%); agreement 136/136; no internal errors.
- [x] All labels/categories and approved-reviewer gates pass; thresholds are unchanged.
- [x] Results record tested code, content and dataset versions. `dev-draft.json` stays historical.

## CI verification

- [x] 8a0bb40 adds `evaluate --set dev --gate B` to the Python job without `--draft`.
- [x] [Run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416)
  succeeds for Python, Node and container smoke after d673400 fixes pool-test teardown.
- Thomas reports 722 Linux tests passed, including the memory-limit test. Earlier assertions
  passed too; the test's competing worker reap caused the cleanup failure, now fixed.
- Python CI covers lint, formatting, types, tests, content, generated/dev gates and docs.
  Node covers tool tests and compiled-content consistency; container smoke also passes.
- Remaining GitHub Node 20/Ubuntu deprecation notices are warnings, not gate failures.

## Reproducing and publishing

Run from `.claude/worktrees/milestone-b`; use the commands in the workflow and
[evaluation guide](../../../../../../evals/verifier/README.md). Set `MATHTUTOR_GIT_SHA` to
the tested code commit before recording a new release result. Do not relabel to fit output.
Only reviewed dev results may appear on the resume; this is not held-out final evaluation.
New wrong answers remain optional and need mathematical labels/human review before evaluation.

## Remaining merge steps

- [x] Commit/push this docs update and retain required green checks.
- [x] Tasks 1–9 merged to `main` in 102a22f, keeping milestone-b's `handoff.md`; CI run 39506433419 green.
- [x] Live `/healthz` and `/readyz` return 200 (2026-10-20); the host still runs milestone A.

No assistant co-author trailers. Tasks 10–16 (practice loop, accounts, UI and deployment)
remain separate; do not describe the full milestone B application as shipped.
