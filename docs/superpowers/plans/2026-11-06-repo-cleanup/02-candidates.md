# Cleanup: doc and script candidates

[Plan](README.md)

275 tracked Markdown files and 164 Python files on 2026-11-06. No module under `src/` is
unused (each is imported or run with `-m`); the four `tools/` scripts are in use.

| # | Group | Files | Why stale | Proposal |
|---|---|---|---|---|
| G1 | Original practice-loop plan and design | 40 md | Superseded unapproved draft | deleted; [recovery](../../../history.md) |
| G2 | `docs/handoff/` | 22 md | Historical goals and decisions still have unique context | keep |
| G3 | `docs/superpowers/plans/portfolio-mvp/milestone-a/` | 11 md | Implementation chronology not proved redundant | keep |
| G4 | `docs/superpowers/plans/portfolio-mvp/milestone-b/` | 33 md | Verification and host evidence still cited | keep |
| G5 | Old B reviews | 31 md + 6 py | Findings and dispositions are dated evidence | keep |
| G6 | C1 review probes | 2 py | Empty `test_review_probes.py` stub; passing recheck probes | delete stub, keep recheck probes |
| G7 | `docs/superpowers/specs/2026-10-13-portfolio-core/` | 10 md | Approved contracts still cited | keep |

Keep (current or cited evidence): root `README.md`, `handoff.md`, `docs/decisions/`,
`docs/ops/`, `evals/`, `content/`, `contracts/`, milestone C plans/specs/reviews from
2026-10-26 on, `docs/verifier/`, and this plan's siblings.

Actual effect so far: 40 Markdown files and one empty Python stub removed. No additional
candidate is marked for deletion without a stronger duplication audit.
