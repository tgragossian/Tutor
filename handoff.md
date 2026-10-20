# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-20 against `milestone-b` 9b2e1f2.
Use this worktree's handoff: `.claude/worktrees/milestone-b/handoff.md`.

## Current state

- `main` contains milestone A. Milestone B is not merged or deployed; the last
  [host record](docs/ops/host.md) serves the skeleton. Deployment was not rechecked here.
- Tasks 1–8 and R22/R23 are implemented. Tasks 10–16 are not started.
- Task 9's human review is complete: 9b2e1f2 records all 136 source rows as `tg`.
  Reviewed labels: 49 correct, 50 incorrect, 37 unsupported. Preserve those marks.
- R24 is approved and restored in dee61a0, but not implemented. Captured `dev.jsonl`
  still has pre-R24 labels and 136 `pending` reviewers; it must be regenerated.
- Task 9 is not complete: R24, content updates, recapture, dev CI gate and release evidence
  remain. See [execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md).

## Next action

Follow the [R24 checklist](docs/superpowers/plans/portfolio-mvp/milestone-b/r24/README.md):

1. Write failing tests, then implement the approved numeric-only precision pre-check.
2. Update problem 253's statement and compiled content; recapture the reviewed dev set.
3. Run `evaluate --set dev --gate B` without `--draft`, record actual results and enable CI.
4. Complete task 9 and merge tasks 1–9 to `main` after checks pass, so the repository link
   exposes the verifier. The practice application still needs tasks 10–16 before deployment.

## R24 scope: do not reinterpret

- Only numeric problems explicitly requesting N decimal places enforce exactly N places
  on standalone decimals. Exact fractions/expressions remain allowed.
- Too many or too few places produce `wrong_decimal_places`, a format issue, not incorrect.
- Read original LaTeX to preserve trailing zeros; value disagreement with MathJSON abstains.
- **No universal decimal-place cap.** Decimals inside expressions stay exact rationals.
  Do not round coefficients or fractions; the eight decimal near-miss traps stay incorrect.
- Removable holes follow [decision 0001](docs/decisions/0001-delivery-verifier-attribution.md):
  ignore only provably removable holes by default; domain/range problems use `strict_domain`,
  including undefined nested denominators such as `1/tan`.
- Dropping R24 was a misunderstanding. The approved
  [R24 spec](docs/superpowers/specs/2026-10-20-decimal-places-design.md) remains in force.

## Evidence and limits

- The pre-R24 136-case draft reported FA 0/54, FR 0/52, coverage 52/52 and agreement 136/136.
  Stored `dev-draft.json` is an older 131-case artifact; neither is release evidence.
- No reviewed R24 gate result exists yet. With 50 incorrect labels, **if** FA stays zero,
  the result would be 0/50 with a 95% Wilson upper bound about 7.1%. This is not measured yet.
- Only the reviewed release result may go on the resume. Do not reuse 0/54 for R24.
  Additional realistic errors are optional; label and human-review them before evaluation.
- Historical tests and review dispositions are in
  [execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md).
  No verifier tests or release evaluation were rerun in this documentation-only update.
- Linux containment, container/browser checks and host sizing remain release obligations.

## Navigation and working rules

- [Documentation](docs/README.md) → [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md)
  → [milestone B tasks](docs/superpowers/plans/portfolio-mvp/milestone-b/README.md).
- [Approved contracts](docs/superpowers/specs/2026-10-13-portfolio-core/README.md),
  [rulings R7–R24](docs/superpowers/plans/portfolio-mvp/milestone-b/02-execution-rulings.md),
  [review sheet](evals/verifier/human/REVIEW.md), [follow-ups](docs/superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md).
- Tasks 12–14 still need atomic revisions, pending replay responses, 422 kind checks and
  friendly format messages. Task 15 adds reviewed content; task 16 owns deployment/sizing.
- Never relax FA 0 or containment. Record actual hours in [hours](docs/ops/hours.md);
  at the 30-hour checkpoint, resolve scope/date/contingency with Thomas.
- Keep every Markdown file at most 100 lines; split by responsibility and link each child
  from its parent. Keep historical evidence dated and separate from current status.
- No assistant co-author trailers; acknowledge assistance in [README](README.md#acknowledgments).
  Describe the verifier as proof-based/SymPy; do not call the tutor LLM-based.

## Preserved references

- [Original handoff](docs/handoff/README.md), [original design](docs/superpowers/specs/2026-10-13-core-practice-loop-design.md),
  [original tasks](docs/superpowers/plans/2026-10-13-core-practice-loop.md), [reviews](docs/reviews/README.md).
- Option B remains: practice on three topics → evaluated RAG hints → operations/final
  evaluation, then the [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md).
