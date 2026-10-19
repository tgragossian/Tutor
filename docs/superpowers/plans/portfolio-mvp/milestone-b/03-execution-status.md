# Milestone B: execution status

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md) · [Follow-ups](05-follow-ups.md)

Updated 2026-10-19 against `milestone-b` 2ad5514; implementation through a115846.
Worktree: `.claude/worktrees/milestone-b`; no milestone B deployment or merge is claimed.
Implementation uses task-by-task spec/quality reviews and fix rounds.

## Tasks

| Task | Commits | State |
|---|---|---|
| 1 Carry-overs, exact decimals | b03faac..813597c | complete |
| 2 Types, bounds, pre-checks | 813597c..b5c05b9 | complete |
| 3 Translator | b5c05b9..ee4f4bf, b7f23ad | complete; B-C2 fixed |
| 4 Equivalence | ee4f4bf..dbeea51 | complete after two fix rounds |
| 5 Refute and check | dbeea51..9d06779, 8346d2a | complete; B-C1 fixed |
| 6 Content check, statement HTML | 9d06779..4ec38cb | complete after one fix round |
| 7 Verifier pool | 4ec38cb..10611a5 | complete; pool fixes and B-C3 fixed |
| 8 Evaluation runner and generated gate | 55744b8, 4138181 | complete; capture support refined in a115846 |
| R22/R23 | ea6748b..19db4ab | complete; [plan](r22-r23/README.md), [decision 0003](../../../../decisions/0003-function-parentheses.md) |
| 9 Human dev cases | a115846, recapture | steps 1–3 drafted (136 cases); step 4 human review pending |
| 10–16 | — | not started |

Checked steps in tasks 1–8 record completion under rulings/review fixes, not literal
execution of every old pseudocode example. Task 9 steps 4–7 and tasks 10–16 stay unchecked.

## Current evidence and limits

- Fresh `uv run pytest -q`: **673 passed, 1 skipped, 1 warning** on Windows, 2026-10-19.
  Skip: Linux-only memory limit. Warning: existing Starlette/httpx deprecation.
- Fresh draft run after R22/R23: 136 cases; 52 correct, 54 incorrect, 30 unsupported,
  every reviewer `pending`. FA 0/54 (95% upper bound 6.6%); FR 0/52 (upper bound 6.9%);
  coverage 52/52 (100%); unsupported accepts 0/30; agreement 136/136; no internal errors.
  Draft metrics pass B; the release gate fails because no row is reviewed.
- The committed [dev-draft.json](../../../../../evals/verifier/results/dev-draft.json) is the
  older 131-case run (FR 2/52, coverage 43/52) and was left unchanged.
- No [disagreements](../../../../../evals/verifier/human/REVIEW.md) remain (`d-explog-03` resolved by 19db4ab).
- CI currently runs the generated gate only; the reviewed dev gate belongs to task 9 step 5.
- Linux containment, browser behavior, Docker build and host memory were not verified here.

## Codex review dispositions

- Historical [2026-10-15 code review](../../../../reviews/2026-10-15-milestone-b/01-code-review.md):
  B-C1 8346d2a, B-C2 b7f23ad, B-C3 plus seven pool failures 10611a5; fixed 2026-10-18.
  Old 474/531 test counts describe earlier commits, not the current branch.
- [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md): B-E1 and B-E2
  fixed in bdb1710; `d-log2-01` fixed in 832740f (fresh draft: FR 1/52, coverage 44/52).
- `d-181-05` resolved by Thomas (R22 option A). The seven domain abstentions now grade correct
  under R23 and 19db4ab. See [follow-ups](05-follow-ups.md).

## Next actions and human gates

1. Thomas reviews every label of the 136 task 9 cases; record resolutions independently of verifier outcomes.
2. Claude addresses review gaps, regenerates reviewed captures, enables the dev CI gate,
   records passing `dev-b.json`, and finishes task 9. Do not count pending cases as reviewed.
3. Task 10 may start during review; task 15 waits for task 9 and tasks 13–14.
4. Thomas reviews new problems in task 15 and performs host deployment/sizing in task 16.

Record actual hours in the [hours log](../../../../ops/hours.md); no B actuals are supplied.
At 30 h, stop at the next task boundary for a scope/date/contingency decision with Thomas.
