# Cleanup: doc and script candidates

[Plan](README.md)

275 tracked Markdown files and 164 Python files on 2026-11-06. No module under `src/` is
unused (each is imported or run with `-m`); the four `tools/` scripts are in use.

| # | Group | Files | Why stale | Proposal |
|---|---|---|---|---|
| G1 | `docs/superpowers/plans/core-practice-loop/`, `plans/2026-10-13-core-practice-loop.md`, `specs/core-practice-loop/`, `specs/2026-10-13-core-practice-loop-design.md` | 40 | Original plan, replaced by option B on 2026-10-13; "reference only" | delete |
| G2 | `docs/handoff/` (00–20 + README) | 22 | Historical handoff; root `handoff.md` is current | delete; move any still-true fact into `handoff.md` or a decision |
| G3 | `docs/superpowers/plans/portfolio-mvp/milestone-a/` | 11 | Milestone A closed 2026-10-15 | delete |
| G4 | `docs/superpowers/plans/portfolio-mvp/milestone-b/` | 33 | Milestone B closed 2026-10-26; `07-verification-evidence.md` is cited by `handoff.md` | delete, after its cited evidence moves to `evals/verifier/results/` |
| G5 | `docs/reviews/2026-10-13/`, `2026-10-15-milestone-b/`, `2026-10-19-milestone-b/`, `2026-10-21-milestone-b/`, `2026-10-22-milestone-b/` | 31 md + 6 `repro_*.py` | Milestone B reviews, all dispositioned | delete, or keep only each README + dispositions page |
| G6 | `docs/reviews/2026-10-27-milestone-c1/test_review_probes.py`, `test_recheck_probes.py` | 2 py | Codex's C1 recheck item 4: "retire or rewrite"; superseded by tests under `tests/` | delete; fix `docs/ops/debugging/c1/03-evaluation.md:23` |
| G7 | `docs/superpowers/specs/2026-10-13-portfolio-core/` | 10 | Spec for A/B; partly still cited for contracts | Codex to decide: keep the contract pages, drop the rest |

Keep (current or cited evidence): root `README.md`, `handoff.md`, `docs/decisions/`,
`docs/ops/`, `evals/`, `content/`, `contracts/`, milestone C plans/specs/reviews from
2026-10-26 on, `docs/verifier/`, and this plan's siblings.

Rough effect: about 140 of 275 Markdown files and 8 Python files removed.
