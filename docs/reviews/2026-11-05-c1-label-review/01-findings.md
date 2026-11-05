# C1 label review: Codex dispositions (2026-11-05)

[Brief](README.md) · [C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md)

## R1 — Holdout integrity: accepted with disclosure

`rq-hold-05` gained `c1-3.8-ex1` under the newly written procedure-label rule. The local
`evals/help/holdout-claims/` directory has no claim, and no holdout `run.json` or `started.json`
was found under `evals/help/results/`. The runner rejects holdout `--retrieval-only` and claims
the partition before scoring. This pre-run label edit is allowed by that protocol. The earlier
draft-holdout BM25 score of 0.576 was already exposed and must stay disclosed; do not present
the eventual holdout as entirely uninspected.

## R2 — How-to rule: clarification needed before the paid run

The rule says a procedure query gets the "first worked example," but `rq-dev-23` uses section
3.9 example 8 and `rq-dev-24` uses section 4.1 example 2 part 1, while both sections have an
earlier example. The likely intent is the first example directly teaching the named procedure,
not the first example in the section. State that precisely and recheck the labels. In
particular, `rq-dev-17` includes the chain-rule procedure (`c1-3.6-rule2`) but no worked
example; `rq-hold-08` describes applying L'Hôpital's rule to 0/0 but has no worked example
(`c1-4.8-ex1` exists). `rq-dev-07` asks for a definition and `rq-dev-18` for a formula, so
they need no example under the narrower rule. `rq-dev-24` should also be checked against
`c1-4.1-ex1`: the chosen `ex2-p1` covers only the first setup step. No labels were edited here.

## R3 — New IDs and counts: accepted

All six new passage IDs exist in the committed corpus. They are in the query's home section,
and every development and holdout query has one to three relevant IDs. Their text supports
the cited topic; the policy question in R2 is about selection, not nonexistent passages.
`test_eval_drafted_sets.py` passed 7/7 after the label edits.

## R4 — Metric and gate text: corrected

The free dev retrieval command reproduced Recall@6 0.7738, MRR@6 0.6732 and Hit@6 0.9643
over 28 queries. The C1 status, eval README and runbook now say 0.7738. The predeclared
holdout gate remains 0.80. The handoff already carried the new value.

## R5 — Key-dependent test: fix queued

`test_settings_defaults` constructs `Settings()` and asserts the API key is absent, so it
fails when `MATHTUTOR_ANTHROPIC_API_KEY` is set for the paid run. This is test isolation,
not evidence of a product failure. Clear that variable via `monkeypatch` in the test before
the paid-run environment is used for tests. No test code was changed in this review.

## R6 — Documentation: accepted

All repository Markdown files are at most 100 lines after these edits. Links added in this
review resolve within the documentation tree; the new prose uses US spelling. `git diff
--check` reports no whitespace errors.

## Resolution (Claude, Thomas approved, 2026-11-05)

R2: rule now reads "a query asking how to carry out a method also gets the home section's first
worked example applying that method." `rq-dev-24` → `c1-4.1-rule1`, `c1-4.1-ex1` (Example 4.1);
`rq-hold-08` adds `c1-4.8-ex1` (pre-run, by rule). `rq-dev-17` names a rule, so it is unchanged.
R5: `test_settings_defaults` clears the key with `monkeypatch`; it passes with the key set.

Step 2 (wording and reveal) findings: [03-step2-findings.md](03-step2-findings.md).
