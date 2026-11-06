# 2026-11-06 C1 release review: Codex brief

[Reviews](../README.md) · [C1 status](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md) ·
[C1 rulings](../../superpowers/plans/portfolio-mvp/milestone-c/c1/21-rulings.md) ·
[Tuning list](../../superpowers/plans/portfolio-mvp/milestone-c/c1/22-tuning.md) · [Handoff](../../../handoff.md)

Scope: `main` from `0448f7b` (Codex's step 2 review) to `HEAD`. C1 is live as a beta since
2026-11-06 on `8b35584`; later commits are not yet deployed unless the handoff says so.
Record findings in `01-findings.md` beside this file as `R1`, `R2`, ... with a disposition.

## What changed

| Commit | Change | Check |
|---|---|---|
| `3bb2b9c` | R38: `max_output_tokens` 1000 → 3000 (config c1-2); Haiku 5.5's thinking counts against `max_tokens` and filled the cap on 8/42 first calls in dev run 1. Tests derive worst cases from the config | worst-case and spend-cap arithmetic; no test still pins a stale constant |
| `8b442d0` | Dev run 2 audited by Thomas (31 rows; 8 overrides); R39 ships Sonnet 5.5 as a beta despite the selection rule; judge rubric v2 (`useful` excludes confusing/self-contradicting help; explain must not set up the problem) | rubric v2 changes only `useful`; judge uses v2; dev used v1, holdout v2 (disclosed) |
| `1de6f3b` | Freeze commit for the holdout | |
| `0b4e729` | Holdout `20261106-005314-holdout` (Sonnet only, $0.53), audited 8/8; config c1-3: live model Sonnet, `month_budget_micros` 10,000,000 | claim file written before scoring; `audit.csv` human columns = judge where Thomas agreed (explicit agreement, so judge-human agreement counts them) |
| `fe3c4c8`, `8b35584` | Codex's uncommitted handoff pointer committed, then `milestone-c1` merged; conflicts in `handoff.md` (took C1's) and `05-expansion-queue.md` (kept both) | C-O7/C-O8 lines survived; full CI passed on the merge |
| `d45c859` | Host measurement: smoke and help e2e passed; memory 78% of 1 GB; 20 simultaneous hints → 6/8 grading `verifier_busy` (1/8 without help) | C-O3 conclusion (stay on 1 GB) and the disclosed CPU contention |
| `3556970` | Released: live check on 3.6-221 (cited feedback, level-1 hint) | abstention not triggerable live in C1; holdout 3/4 stands in |
| `0e81e1a`, `3bc591d` | Tuning list (13 items) from audits and Thomas's live testing | |
| `cfb46ca` | **R40** prompt fix and answer-box CSS/JS fix (below) | **main focus** |

## R40 (the main item to review)

Thomas tested 5x³ − x + 1 with `15x^2-3` then `15x-1`. The prompt listed attempts newest
first as `1.`, `2.` and the task said "the first one listed"; the help coached the earlier
attempt (it called `15x^2-3` the latest). Now `prompts._context_block` lists oldest to newest
with `LATEST attempt:` / `Earlier attempt N:` labels and a "help with the LATEST attempt"
line; `feedback.md`, `hint.md`, `hint_choice.md` say "the one marked LATEST"; `LEVEL_RULES[1]`
praises only a part fully correct in the latest attempt. `HelpContext.attempts` stays newest
first (retrieval's C1-R6 query depends on it). Test: `test_latest_attempt_is_marked_and_listed_last`.

Please check:
1. Nothing else reads the attempts as "first listed" (judge prompt, eval report, retrieval).
2. The judge's own prompt says "oldest first" (`judge.py`); confirm the judge still reads the
   latest attempt correctly, and whether its wording should match the new labels.
3. Shipping a prompt change after the one-shot holdout, re-checked on dev only (dev run 3,
   Sonnet, results in `evals/help/results/`), is disclosed in R40. Is the disclosure enough,
   and should a fresh holdout partition be drafted for prompt v1.1?
4. Only 10/66 cases have two or more attempts; propose dev cases for the swap pattern
   (tuning item 1) without changing the pinned 42/24 mix silently.

## Answer box

`app.css` styles every `math-field[read-only]` inline (for math in statements and help). The
answer box is set read-only while a check runs; MathLive left the attribute after unlock, so
the box stayed small. Now `#answer-field[read-only]` keeps the block frame, and
`setFieldReadOnly()` clears the attribute on unlock. Check: locked styling still signals
"checking" (it no longer changes size), and choice radios are unaffected.
