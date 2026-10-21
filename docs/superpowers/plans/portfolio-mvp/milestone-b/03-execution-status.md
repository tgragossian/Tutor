# Milestone B: execution status

[Milestone B plan](README.md) · [Execution rulings](02-execution-rulings.md) · [Follow-ups](05-follow-ups.md)

Updated 2026-10-21. Tasks 1–9 merged to `main` (102a22f); tasks 10–14 complete on `milestone-b`
(not pushed); task 15 partial; task 16 not started. No B deployment claimed.

## Tasks

| Task | Commits | State |
|---|---|---|
| 1 Carry-overs, exact decimals | b03faac..813597c | complete |
| 2 Types, bounds, pre-checks | 813597c..b5c05b9 | complete |
| 3 Translator | b5c05b9..ee4f4bf, b7f23ad | complete; B-C2 fixed |
| 4 Equivalence | ee4f4bf..dbeea51 | complete after two fix rounds |
| 5 Refute and check | dbeea51..9d06779, 8346d2a | complete; B-C1 fixed |
| 6 Content check, statement HTML | 9d06779..4ec38cb | complete after one fix round |
| 7 Verifier pool | 4ec38cb..10611a5, d673400 | complete; Linux test cleanup fixed |
| 8 Evaluation runner and generated gate | 55744b8, 4138181, bdb1710 | complete; reviewer/category checks included |
| R22/R23 | ea6748b..19db4ab, fe6bd4a | complete; [plan](r22-r23/README.md) |
| R24 | a76985d | implemented with tests first; [checklist](r24/README.md) |
| 9 Human dev cases | 9b2e1f2..8a0bb40 | complete: review, recapture, release result and CI |
| 10 Store | d865179 | complete; amended in 11–12 ([rulings](06-app-track-rulings.md)) |
| 11 Auth | 73ae3af | complete |
| 12 Practice service | 458f2ca | complete; races run 3× clean |
| 13 JSON API | abda25e | complete |
| 14 Pages, MathLive | c52305d | complete; manual browser check passed |
| 15 Content, smoke | 5fd8952 | smoke + CI job done; new problems blocked (see below) |
| 16 Release | — | not started; needs Docker and host |

## Release evidence

- Reviewed source and b5ad4b2 captures match: 136 `tg`, 49 correct / 50 incorrect /
  37 unsupported. `d-sqsq-02` includes zero, `[0, inf)`.
- [dev-b.json](../../../../../evals/verifier/results/dev-b.json), committed in e995438,
  records `evaluate --set dev --gate B` without `--draft` at verifier `0.1.0+b5ad4b2`.
- FA 0/50 (95% upper bound 7.1%), FR 0/49 (7.3%), coverage 49/49,
  unsupported graded correct 0/37 (9.4%), agreement 136/136; no internal errors.
- All seven R24 cases return `wrong_decimal_places`. Problem 253 and compiled content
  explicitly permit an exact answer or rounding to 3 places.
- [Results index](../../../../../evals/verifier/results/README.md) records versions and
  provenance. `dev-draft.json` is historical (131 unreviewed cases), not release evidence.

## CI and containment

- 8a0bb40 adds the reviewed dev gate to Python CI alongside the generated regression gate.
- [Run 39504828416](https://github.com/tgragossian/Tutor/actions/runs/39504828416) at d673400:
  Python, Node and container smoke succeeded; first green milestone-b run.
- Thomas reports 722 tests passed on Linux, including the memory-limit test skipped on Windows.
  Earlier runs failed at pool-test cleanup after passing assertions: `psutil.wait()` reaped
  the killed worker before multiprocessing could. d673400 fixes the test, not production limits.
- Remaining Node 20/Ubuntu deprecation notices are warnings. FA 0 and containment are intact.
- This docs pass inspected commits, workflow and result artifacts; it did not rerun Linux CI
  or live checks. Host sizing and practice-browser validation remain tasks 15–16.

## Review dispositions

- [2026-10-15 review](../../../../reviews/2026-10-15-milestone-b/01-code-review.md):
  B-C1 8346d2a, B-C2 b7f23ad, B-C3 and pool fixes 10611a5.
- [2026-10-19 review](../../../../reviews/2026-10-19-milestone-b/README.md):
  B-E1/B-E2 fixed in bdb1710; `d-log2-01` fixed in 832740f; R22/R23 resolved other disagreements.
- 86cac1d restricts choices to listed IDs; 634c968 suggests both readings of `sin^-1(x)`.
- Thomas reviewed all 136 source rows in 9b2e1f2. R24 and recapture now agree with every label.

## Next actions

1. **Thomas:** decide how to source task 15's 14–24 new problems. Fetching OpenStax pages into
   an LLM conflicts with the book's notice ([source](../../../../../content/sources/openstax-calculus-v1.md)):
   Thomas transcribes statements, or Claude writes `adapted` problems, or written permission.
2. Then draft, `content_check`, Thomas reviews (gate), commit (task 15 steps 1–3, 7).
3. CI's `container` job now fails `/readyz` (`database_unavailable`) until task 16 adds the
   `/data` volume and migrate step; push only with that known, or do task 16's container part first.
4. One whole-branch review (fresh reviewer) after task 16, per the executing-plans skill.

Record actual hours in the [hours log](../../../../ops/hours.md); no B actuals are supplied.
At 30 h, stop at the next task boundary for a scope/date/contingency decision with Thomas.
