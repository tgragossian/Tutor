# Repo cleanup plan and review

[Plans](../README.md) · [Handoff](../../../../handoff.md)

> **Status:** partially executed on `answers-table` after Thomas requested the cleanup.
> [Codex disposition](../../../reviews/2026-11-06-repo-cleanup/README.md) records what was
> deleted and why the other candidate groups remain.

**Why:** AI assistants read outdated plans, handoffs and whole old copies of the repo as if
they were current (Thomas, 2026-11-06: another model got confused by the context). Fewer,
current files make every future session cheaper and more accurate.

**Principles**
- Delete rather than archive in the tree: an `archive/` folder is still read by AI tools.
- Historical text is recoverable: the local tag `archive-2026-11-06` points to `f9a9cbc`;
  any removed file stays readable with
  `git show archive-2026-11-06:<path>`. One short `docs/history.md` lists what went and why.
- Evidence that current docs still cite (verifier results, holdout and audit numbers) stays,
  or its facts move into a current page before the source goes.
- Precedence is unchanged: `docs/decisions/` > `handoff.md` > plans.

## Contents

1. [Local clutter](01-local.md): untracked working state, retained.
2. [Doc and script candidates](02-candidates.md): reviewed group dispositions.
3. [Inbound links](03-links.md): the pre-cleanup reference inventory.
4. [Procedure](04-procedure.md): recovery and completed checks.

The tag has not been pushed. Push it before relying on that name from another machine;
the commit id in [history](../../../history.md) is an independent recovery path.
