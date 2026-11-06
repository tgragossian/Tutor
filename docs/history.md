# Removed documentation

[Documentation](README.md) · [Current handoff](../handoff.md)

On 2026-11-06, the unapproved original core practice-loop draft was removed from the
working tree. The reviewed option B [delivery plan](superpowers/plans/portfolio-mvp/README.md)
and [portfolio-core contracts](superpowers/specs/2026-10-13-portfolio-core/README.md)
supersede it. The [original review](reviews/2026-10-13/README.md) remains for its findings.

The full 40-file draft is preserved at local tag `archive-2026-11-06`:

```text
git show archive-2026-11-06:docs/superpowers/plans/2026-10-13-core-practice-loop.md
git show archive-2026-11-06:docs/superpowers/specs/2026-10-13-core-practice-loop-design.md
```

The two entry points list every child path. To read a child, use
`git show archive-2026-11-06:<path>`. The tag points to `f9a9cbc`, so that commit also
works if the tag is unavailable. The [preservation manifest](reviews/2026-10-13/archive-manifest.json)
records hashes and original line ranges.

Milestone A/B plans, review dispositions, verifier evidence, and the original handoff
remain in the working tree because they contain facts that current pages still cite.

The empty C1 `test_review_probes.py` stub was also removed. Its original pre-fix tests
remain in Git history; current passing regressions live under `tests/`. The separate
`test_recheck_probes.py` still contains active offline reproductions and remains.
