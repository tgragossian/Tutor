# Milestone B: execution status

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md) · [Follow-ups](05-follow-ups.md)

Updated 2026-10-20 against `milestone-b` 9b2e1f2.
Worktree: `.claude/worktrees/milestone-b`; B is not merged or deployed.

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
| 8 Evaluation runner and generated gate | 55744b8, 4138181, bdb1710 | complete; reviewer/category checks included |
| R22/R23 | ea6748b..19db4ab, fe6bd4a | complete; [plan](r22-r23/README.md) |
| R24 | dee61a0 | approved spec; implementation pending; [checklist](r24/README.md) |
| 9 Human dev cases | a115846..9b2e1f2 | steps 1–4 done; recapture and steps 5–7 remain |
| 10–16 | — | not started |

Task 9 step 4 is complete in source YAML, including the seven R24 labels. Steps 5–7
remain open; stale captures do not satisfy the release gate.

## Source, captures and evidence

| Artifact | Observed state at 9b2e1f2 |
|---|---|
| `human/dev.src.yaml` | 136 `tg`; 49 correct, 50 incorrect, 37 unsupported |
| `human/dev.jsonl` | stale: 136 `pending`; 52 correct, 54 incorrect, 30 unsupported |
| `results/dev-draft.json` | historical 131-case artifact: FA 0/54, FR 2/52, coverage 43/52 |
| `results/dev-b.json` | no reviewed release result recorded yet |

Paths above are relative to [evals/verifier](../../../../../evals/verifier/README.md).
Reviewed source also changes `d-sqsq-02` to `[0, inf)`; recapture must carry this domain.

- Historical post-R22/R23 draft: FA 0/54 (95% upper bound 6.6%), FR 0/52, coverage 52/52,
  unsupported accepts 0/30, agreement 136/136. This does not measure R24.
- New labels imply an FA denominator of 50. If FA remains zero, its 95% Wilson upper bound
  is about 7.1%; do not publish this conditional estimate as a reviewed result.
- CI currently runs the generated gate only. Add the dev gate after R24 and recapture.
- Last documented 2026-10-19 Windows test run: 687 passed, 1 Linux-only skip, 1 existing
  Starlette/httpx warning. Subsequent fixes exist; this count is not a test of current HEAD.
- This docs pass did not run verifier tests, evaluation, Linux containment or deployment.

## Review dispositions

- [2026-10-15 review](../../../../reviews/2026-10-15-milestone-b/01-code-review.md):
  B-C1 8346d2a, B-C2 b7f23ad, B-C3 and pool fixes 10611a5.
- [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md):
  B-E1/B-E2 fixed in bdb1710; `d-log2-01` fixed in 832740f.
- R22/R23 resolved the nine earlier disagreements; those outcomes remain historical.
  R24 changes seven expected labels and must be implemented before the next release run.
- 86cac1d restricts choice answers to listed IDs; 634c968 suggests both readings of `sin^-1(x)`.
- Thomas completed all 136 source reviews in 9b2e1f2. Preserve `tg` marks and reviewed labels.

## Next actions

1. Follow the [R24 pre-check checklist](r24/01-precheck.md), with failing tests first.
2. Follow [content, capture and release](r24/02-release.md): update content, recapture,
   verify source/capture agreement, run non-draft gate B, enable CI and record results.
3. Finish task 9, then merge tasks 1–9 to `main` after required checks pass. No B application
   deployment is implied; tasks 10–16 remain separate.
4. Only reviewed gate metrics belong on the resume. More realistic wrong cases are optional
   and require math-based labels plus human review before evaluation.
5. Task 15 waits for task 9 and tasks 13–14; task 16 retains deployment/sizing gates.

Record actual hours in the [hours log](../../../../ops/hours.md); no B actuals are supplied.
At 30 h, stop at the next task boundary for a scope/date/contingency decision with Thomas.
