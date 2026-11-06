# Cleanup: inbound links to fix

[Plan](README.md)

Current files that link into G1–G7 (grep on 2026-11-06, excluding the groups themselves).
Each link is either removed, pointed at a current page, or replaced by
`git show archive-2026-11-06:<path>` in `docs/history.md`. `tools/check_docs.py` must pass.

- `handoff.md`
- `content/review/README.md`
- `docs/README.md`
- `docs/ops/hours.md`
- `docs/ops/debugging/README.md`, `01-app.md`, `02-release.md`
- `docs/ops/debugging/c1/03-evaluation.md` (probe command, G6)
- `docs/reviews/README.md`
- `docs/superpowers/plans/README.md`
- `docs/superpowers/plans/portfolio-mvp/README.md`, `01-foundation.md`, `02-practice.md`,
  `06-ai-decisions-handoff.md`, `milestone-c/03-open-decisions.md`
- `docs/superpowers/specs/README.md`, `2026-10-20-decimal-places-design.md`
- `docs/superpowers/specs/2026-10-13-portfolio-core/README.md`, `02-answer-contracts.md`,
  `07-application-and-web.md`, `08-verifier-evaluation.md`, `09-operations.md` (only if G7 stays)
- `docs/verifier/supported.md`
- `evals/verifier/human/REVIEW.md`, `evals/verifier/results/README.md`

Re-run the grep after deletion; the list may shrink once G7 is decided.
