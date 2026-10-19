# Milestone B: Codex doc-sync request (2026-10-19)

[Milestone B plan](README.md) · [Execution status](03-execution-status.md) · [Handoff](../../../../../handoff.md)

Thomas asked Codex to bring every Markdown file in the milestone B plan tree up to date with
the branch. The docs were last updated at d82fe72 (2026-10-18); three commits have landed since.

## What changed since the docs were last updated

- **Task 8 complete.** 55744b8 (runner, Wilson metrics, generated regression set, CI step) and
  4138181 (gate requires agreement and no crashes; strict case rows; pooled grading; strict
  `loads_exact`). Usage and gate rules: [evals/verifier/README.md](../../../../../evals/verifier/README.md).
- **Task 9 drafted, not reviewed.** a115846 adds 131 draft cases (52 correct, 54 incorrect,
  25 unsupported) in `evals/verifier/human/dev.src.yaml`, captured from real MathLive by
  `tools/capture/eval.mjs` into `dev.jsonl`. Every case has `reviewer: 'pending'`
  (the plan said `''`; record the deviation).
- **Draft metrics** (`results/dev-draft.json`): FA 0 of 54 (upper bound 6.6%), FR 2 of 52 (3.8%),
  coverage 43 of 52 (82.7%), unsupported accepts 0 of 25, agreement 122 of 131,
  0 internal errors. Gate B **fails** on FR and coverage.
- The 9 disagreements and the open label/verifier questions are in the
  [review sheet](../../../../../evals/verifier/human/REVIEW.md) (split into REVIEW-1..4).
  `d-log2-01` is the same x^(log_2 8) case already listed under "B-C fixes" deferred minors.
- Task 9 steps 1–3 are done; step 4 (Thomas reviews every label) is the open human gate;
  steps 5–7 wait on it. Labels were not changed to match the verifier; keep it that way.

## Files to update (all of `milestone-b/`)

- `03-execution-status.md`: task rows for 8 (done, commit range) and 9 (draft, awaiting
  review); test count at a115846 (re-run `uv run pytest -q`, don't copy the old 531);
  replace "Next: task 8" with the real next step; link the draft metrics and review sheet;
  add any task 8/9 deferred minors from the commit bodies.
- `README.md`: plan-files list (add this file); exit-evidence line for tasks 8–9 should note
  the draft result without claiming the gate passes.
- `tasks/01..08-*.md`: tick `- [ ]` → `- [x]` for steps that were done; note in one line
  where a step was replaced by a ruling (R7–R21) or a review fix, rather than rewriting it.
- `tasks/09-dev-cases.md`: tick steps 1–3; note `reviewer: 'pending'` and the 131-case draft.
- `tasks/10..16-*.md`: check only that links, file paths and dependencies still match
  `01-file-map.md` and what tasks 1–9 actually built; fix stale references.
- `00-constraints.md`, `01-file-map.md`, `02-execution-rulings.md`: reconcile with the code
  (e.g. `verify/mutate.py`, `tools/capture/eval.mjs`, `serve.mjs`, `results/` are listed);
  add rulings only if one was actually made, never invent one.
- Outside the tree, keep consistent: `handoff.md` (Claude update / Next), `docs/ops/hours.md`
  (task 9 row; leave actual hours blank for Thomas).

## Rules

- Every `.md` stays at most 100 lines; split into linked sub-files if needed.
- Don't edit the preserved originals (`docs/handoff/`, core-practice-loop spec and plan).
- No assistant co-author trailers in the commit (decision 0001).
- Docs only: don't change code, case labels or results files. Report contradictions
  between docs and code in the status file instead of fixing code.
- Commit on `milestone-b` as `docs: sync milestone B docs through task 9 draft`.
