# Repo cleanup plan (draft: awaiting Codex review)

[Plans](../README.md) · [Handoff](../../../../handoff.md)

> **Status:** draft. Nothing is deleted until Codex has reviewed this list and Thomas approves.
> Record findings in `docs/reviews/<date>-repo-cleanup/` as `K1`, `K2`, ... with a disposition.

**Why:** AI assistants read outdated plans, handoffs and whole old copies of the repo as if
they were current (Thomas, 2026-11-06: another model got confused by the context). Fewer,
current files make every future session cheaper and more accurate.

**Principles**
- Delete rather than archive in the tree: an `archive/` folder is still read by AI tools.
- Nothing is lost: tag first (`archive-2026-11-06`); any file stays readable with
  `git show archive-2026-11-06:<path>`. One short `docs/history.md` lists what went and why.
- Evidence that current docs still cite (verifier results, holdout and audit numbers) stays,
  or its facts move into a current page before the source goes.
- Precedence is unchanged: `docs/decisions/` > `handoff.md` > plans.

## Contents

1. [Local clutter](01-local.md): old worktrees and a junk folder (not tracked by git).
2. [Doc and script candidates](02-candidates.md): groups, counts and a keep/delete proposal.
3. [Inbound links](03-links.md): the 24 current files that link into candidates.
4. [Procedure](04-procedure.md): order of operations and checks.

## Questions for Codex

1. Which candidate groups hold evidence still needed (B verification, C1 review dispositions)?
2. Should old reviews be deleted, or reduced to their README plus dispositions?
3. Any candidate that Codex's own sessions still rely on?
4. Is `docs/history.md` plus a tag enough provenance, or should the tag be pushed to GitHub?
