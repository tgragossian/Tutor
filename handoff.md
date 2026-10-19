# Calculus Tutor handoff

Owner: Thomas Gragossian. Updated: 2026-10-19 (documentation sync and evaluation review).

## Current state and next action

- `main` bb15c91 contains milestone A. The host last recorded in [operations](docs/ops/host.md)
  serves the skeleton at <https://tutor.thomasgragossian.dev>; deployment was not rechecked today.
- Active work: branch `milestone-b`, worktree `.claude/worktrees/milestone-b`.
  Reviewed through 2ad5514 (task 9 code a115846); B is not merged or deployed.
- Tasks 1–8 complete. Task 9 steps 1–3 drafted: 131 cases, all `reviewer: pending`.
  Tasks 10–16 are not started. See [execution status](docs/superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md).
- **Thomas next:** review every label in the [review sheet](evals/verifier/human/REVIEW.md).
  Draft gate B fails: FR 2/52 (3.8%), coverage 43/52 (82.7%); FA 0/54
  (95% Wilson upper bound 6.6%). These are unreviewed development results.
- **Claude next:** address the [2026-10-19 review](docs/reviews/2026-10-19-milestone-b/README.md)
  before completing task 9 steps 4–7 and enabling the reviewed dev CI gate.
  Task 10 can proceed while human review is pending, as the delivery plan permits.
- Documentation sync is complete. Keep every Markdown file at most 100 lines,
  splitting by responsibility and linking each child from its parent.

## What Claude needs to consider

1. The runner accepts `pending` reviewers. Add a reviewed-dev release check and retain
   a separate draft-measurement path; never change labels to pass a gate.
2. Gate B accepts an all-correct dev set and an empty generated set. Add dataset-validity
   checks and regressions; the current dataset is populated, so this is a guard gap.
3. Resolve `d-log2-01`: a computed exponent equal to 3 acquires a positive-base restriction
   and rejects x³ on negative x. Preserve B-C2 resource bounds when improving exact exponents.
4. Resolve `d-181-05` with Thomas: displayed trig input and captured tree differ in meaning.
   Record the input/label decision; track seven conservative domain abstentions separately.
5. Tasks 12–14 still need atomic revisions, pending replay responses, 422 kind checks and
   friendly format messages under R12–R16. These are planned, not implemented.
6. Record actual hours before the 30-hour checkpoint; do not reduce accuracy or containment
   to recover schedule. Linux memory, container/browser checks and host sizing remain gates.

## Verification evidence

- Fresh Windows run on 2026-10-19: **576 passed, 1 skipped** (Linux memory limit), one
  existing Starlette/httpx warning. See [review evidence](docs/reviews/2026-10-19-milestone-b/README.md).
- Earlier B-C1/B-C2/B-C3 fixes: 8346d2a, b7f23ad, 10611a5 respectively;
  the [2026-10-15 review](docs/reviews/2026-10-15-milestone-b/README.md) is historical.
- No code, case labels or result files changed in this documentation pass.
- Markdown links/line limits and the maintained documentation tree pass validation.

## Accepted direction and precedence

Option B: deployed skeleton → practice on three topics → evaluated RAG hints → operations
and final evaluation. Then diagnostic → exam/recap → all 15 topics → extraction → LoRA.
The initial 160-hour target does not promise the full expansion queue.
First practice release: 20–30 reviewed problems, accounts, history and one mode;
basic derivatives, trig derivatives and chain rule; FastAPI/Jinja, MathLive, SQLite, Docker.
See the [delivery plan](docs/superpowers/plans/portfolio-mvp/README.md) and [expansion queue](docs/superpowers/plans/portfolio-mvp/05-expansion-queue.md).

[Decision 0001](docs/decisions/0001-delivery-verifier-attribution.md) governs verifier semantics:
equality on the real domain, ignoring only provably removable holes, with strict overrides.
Keep raw restrictions; unknown domain proofs abstain; numerical agreement never proves equality.
Polynomial implicit differentiation is retained for topic expansion, with exact reduction,
denominator/regularity checks and coverage of every included branch.

Use the [approved spec](docs/superpowers/specs/2026-10-13-portfolio-core/README.md) and
[execution rulings R7–R21](docs/superpowers/plans/portfolio-mvp/milestone-b/02-execution-rulings.md)
with the active plan. Rulings supersede original task recipes; review suggestions are not rulings.
Thomas approved milestone B and selected subagent-driven implementation; this pass is docs only.
No assistant coauthor trailers; acknowledge assistance in the [README](README.md#acknowledgments).

## Preserved references

- [Original handoff](docs/handoff/README.md), [original design](docs/superpowers/specs/2026-10-13-core-practice-loop-design.md),
  [original tasks](docs/superpowers/plans/2026-10-13-core-practice-loop.md), [original review](docs/reviews/2026-10-13/README.md).
- Original wording remains preserved except the recorded commit-attribution amendment.
