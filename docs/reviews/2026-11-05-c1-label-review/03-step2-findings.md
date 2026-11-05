# C1 step 2 review: Codex dispositions (2026-11-05)

[Brief](02-step2-brief.md) · [Label findings](01-findings.md) ·
[C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md)

## S2-1 — Core level-0 instructions agree; older design text needs updating

`LEVEL_RULES[0]`, `START_RULES[2]`, `prompts/v1/system.md` and rubric v1 all say step 1
asks about form without naming the method and step 2 names the fitting method without doing
the work. The prompt fingerprint is computed from these files; tests pin its format, not its
old value. The C design's `02-help-flow.md` and the R35 row in `21-rulings.md` still say
"rule and first move / concrete setup"; a service-test comment does too. Mark R35's wording
superseded by R37 and update the design text before release. No source text was changed here.

## S2-2 — Holdout notes: accepted with the existing disclosure

The four edits change only judge notes, not attempts, tags or expected abstentions. No local
holdout claim or run marker exists. The pre-run wording alignment is allowed; retain the
disclosure that a draft holdout retrieval score was previously seen. Do not relabel notes
after the one-shot run to improve its result.

## S2-3 — Ten notes: accepted

The six dev and four holdout notes distinguish step 1 from step 2, identify observable
features a judge can grade, and retain the leak limits for dev-18, dev-26, dev-35 and
hold-15. Step-2 notes name methods without working the problem. The focused Python tests
passed 23/23 (reviewed sets, hint ladder and prompt fingerprint).

## S2-4 — Show answer: UI path accepted, API remains one action

The first click only arms and displays the warning; the second calls `act('reveal')`.
Render disarms on a new item, after reveal, and when reveal is unavailable. A rapid double
click still passes through the warning synchronously. The warning has `role=status`; the
Hint suggestion is conditional. Node tests passed 49/49. Integration tests call the reveal
API directly after exhaustion; the two-click rule is a browser interaction, not a server
restriction. Describe it that way in release copy.

## S2-5 — Citation title: visible caveat, change recommended

`source_ref()` includes the section title and the browser shows it. A level-0 step-1 hint
from section 3.6 can therefore display "3.6 The Chain Rule" beneath a body that carefully
avoids naming the rule. This weakens R37 in the delivered experience. Consider a section
number-only help citation label for step 1 while retaining the OpenStax link and license;
otherwise disclose that R37 governs the hint body, not the visible citation. No UI or
evaluation code was changed in this review.

## Resolution (Claude, Thomas approved, 2026-11-05)

S2-1: R35 row marked superseded by R37; `02-help-flow.md`, `eval/cases.py` and a service-test
comment updated. S2-4: release copy will call the two clicks a browser step, not a server rule.
S2-5: option 1 chosen: every help citation reads `Calculus Volume 1, §<section>` (link and
license kept), matching the problem's own source line. Tests updated; help, integration and web
suites pass.
