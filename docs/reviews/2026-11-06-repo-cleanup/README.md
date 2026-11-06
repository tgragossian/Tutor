# Repo cleanup: Codex review and disposition

[Plan](../../superpowers/plans/2026-11-06-repo-cleanup/README.md) · [Removed files](../../history.md)

The original G1 practice-loop draft was unapproved, explicitly reference-only, and
superseded by the reviewed option B plan and portfolio-core contracts. Its 40 Markdown
files were removed from this branch after tagging the pre-cleanup head as
`archive-2026-11-06` (`f9a9cbc`). The empty G6 `test_review_probes.py` stub was also
removed; the passing recheck probes remain. Inbound Markdown links were repaired.

| Group | Disposition | Reason |
|---|---|---|
| G1 | Delete done | Superseded draft; recoverable at the tag and indexed in `docs/history.md`. |
| G2 | Keep | Historical handoff contains original goals and decisions not fully represented in the current handoff. |
| G3 | Keep | Milestone A plan records scope and implementation chronology. No line-by-line duplication proof. |
| G4 | Keep | B status and verification evidence carry release/CI distinctions and host claims absent from the result artifact. |
| G5 | Keep | Reviews contain findings, dispositions, reproductions, and dated validation; pruning them risks losing why fixes were made. |
| G6 | Partial | Empty original probe stub deleted; active `test_recheck_probes.py` retained. |
| G7 | Keep | Approved A/B contracts are still cited by content, verifier, security, and evaluations. |

The four old worktrees and untracked browser output were left untouched: they are local
working state, not redundant tracked Markdown. No branch was merged, deployed, or pushed.
The recovery tag is local; push it before relying on the tag from another machine.
