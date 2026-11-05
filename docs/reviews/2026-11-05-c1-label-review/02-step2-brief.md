# C1 step 2 (wording approvals): Codex brief (2026-11-05)

[Brief](README.md) · [Findings](03-step2-findings.md) ·
[C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md) ·
[C1 rulings](../../superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md)

Base `e41ea8b` (label review committed). Changes below are uncommitted on `milestone-c1`
until this review passes; the paid dev run (step 3) follows directly.

## Approved by Thomas as is

Help panel copy, provider disclosure (Claude; Clear history erasing help text checked at
`application/practice.py:233`), levels 1–3, the four mistake types, `hint_choice.md`, and the
four misconception notes (math rechecked: each wrong answer follows from its stated mistake).

## Changed

| Change | Files |
|---|---|
| **R37 level 0:** step 1 asks one question about the problem's form without naming the rule or starting the work; step 2 names the rule or method that fits and why | `help/prompts.py` (`LEVEL_RULES[0]`, `START_RULES[2]`), `prompts/v1/system.md`, `evals/help/rubric/v1.md`, comments in `help/context.py`, `help/service.py` |
| Case notes rewritten to R37 (judge expectations only; inputs unchanged) | dev-01, 11, 12, 18, 26, 35; hold-01, 07, 15, 18 |
| Confusion label `trig_ladder` reworded to "How do the derivatives of sin and cos repeat?" (id unchanged) | `content/help/confusions.json` |
| Show answer takes two clicks: the first shows a warning ("…at least 15 minutes, or if you can't find where to start."), plus " Try Hint first." only when the Hint type is offered | `web/templates/practice.html`, `web/static/practice.js`, `tools/web/practice_controller.test.mjs` |
| Rulings and status | `21-rulings.md` (R37), `20-status.md` (step 2 approved) |

Validation: full Python suite 1645 passed, 3 skipped (key set in the shell); web tests 49/49;
`check_docs.py` and `git diff --check` clean. No provider call was made.

## Please check

1. **Prompt consistency.** `LEVEL_RULES[0]`, `START_RULES[2]`, `system.md` and the rubric say
   the same thing; nothing else (tests, docs, prompts) still describes level 0 as "rule and
   first move." The prompt fingerprint changes; confirm nothing pins the old value.
2. **Holdout notes.** hold-01, 07, 15, 18 notes changed before any holdout run, to match a
   predeclared wording change, not results. Confirm this is allowed like R1 of the findings.
3. **Note quality.** Each rewritten note is gradable by the judge and consistent with R37
   (step 1 never names the rule; step 2 names it without carrying out a step). Leak cautions
   from the old notes are kept (dev-18, dev-26, dev-35, hold-15).
4. **Show answer.** The warning resets on a new item, after a reveal and when reveal is not
   allowed; a double click cannot skip the warning; screen readers announce it (`role=status`).
   Does any server or e2e path assume one click?
5. **Citation caveat.** Help sources are labeled by section title, so chain-rule items still
   show "3.6 The Chain Rule" (as do the problem source and topic). Accept as known, or flag.

Findings and resolution: [03-step2-findings.md](03-step2-findings.md).
