# R24: content, capture and release

[R24 checklist](README.md) · [Pre-check](01-precheck.md) · [Evaluation guide](../../../../../../evals/verifier/README.md)

Status: planned. Run commands from `.claude/worktrees/milestone-b` after implementing R24.

## Content and capture

- [ ] Add “Give an exact answer or round to 3 decimal places.” to problem 253's statement.
  Audit other numeric problems with `precision.decimals` for matching instructions.
- [ ] Recompile with `npm run compile --prefix tools`; never hand-edit compiled JSON.
- [ ] Preserve 136 `tg` source reviews: 49 correct, 50 incorrect, 37 unsupported.
  The seven R24 labels and `d-sqsq-02`'s `[0, inf)` domain were reviewed in 9b2e1f2.
- [ ] Run `npm run capture:eval --prefix tools` using real MathLive/Chromium.
- [ ] Compare source/capture IDs, reviewers, labels, rationales and inline domains.
  Confirm all captured reviewers are `tg`; inspect `raw_latex` for `d-253-02`.
- [ ] Refresh review-sheet outcomes from actual results, keeping pre-R24 evidence dated.

## Checks and release gate

Run repository checks after the focused R24 tests:

```text
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
npm test --prefix tools
uv run python -m mathtutor.verify.content_check
uv run python -m mathtutor.verify.evaluate --set generated --gate B
uv run python tools/check_docs.py
```

Set `MATHTUTOR_GIT_SHA` to the tested implementation commit; do not label uncommitted code
as that commit. Run the release evaluation without `--draft`:

```text
uv run python -m mathtutor.verify.evaluate --set dev --gate B --out evals/verifier/results/dev-b.json
```

- [ ] Require exit 0: FA 0, unsupported accepts 0, FR ≤ 2%, coverage ≥ 85%, no crashes,
  required labels/categories and approved reviewers. Do not weaken these gates.
- [ ] Inspect every disagreement; fix bugs or obtain a human label ruling.
  Never relabel solely to agree with the verifier.
- [ ] Add `evaluate --set dev --gate B` to `.github/workflows/ci.yml`; obtain required CI
  results including Linux containment and container checks. Windows skips are not evidence.
- [ ] Record code/content/dataset versions and measured counts in task 9, status and handoff.
  Keep the old draft artifact explicitly historical.

## Metrics and merge

- Before R24: the 136-case draft reported FA 0/54 (95% upper bound 6.6%).
- Reviewed labels now have 50 incorrect cases. If FA stays zero, the upper bound is about
  7.1%; only the actual reviewed gate result may go on the resume.
- More realistic wrong answers are optional, not a release requirement or a way to select
  a preferred denominator. Establish math labels and human review before evaluation.
- [ ] Finish task 9 steps 5–7, commit without assistant co-author trailers, and merge tasks
  1–9 to `main` after checks pass. Verify the repository link exposes those commits.
- Tasks 10–16 and public practice deployment remain unfinished; merging the verifier track
  does not mean milestone B is fully shipped.
