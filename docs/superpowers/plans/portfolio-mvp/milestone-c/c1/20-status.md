# C1 status: pre-release (2026-10-28)

[C1 plan](README.md) · [Gates](02-gates.md) · [Runbook C1](../../../../../ops/runbook-c1.md) ·
[Open register](../03-open-decisions.md)

Tasks 1 to 15 are implemented on branch `milestone-c1`; reviewed by subagent per task. The
branch is **not released**: nothing is deployed, no holdout has run and no key is on the host.
[Codex review](../../../../../reviews/2026-10-27-milestone-c1/README.md) of `3be5808` found nine
issues (five original P1 blockers). [Codex recheck at b16a206](../../../../../reviews/2026-10-27-milestone-c1/07-recheck.md)
initially reopened R4/R7; both are now [fixed locally](../../../../../reviews/2026-10-27-milestone-c1/11-debugging-fixes.md).
All nine findings are closed at code level. Owner/provider/container gates remain; carry
these local changes into C2 and review its plan before implementation.

## Done

| Area | State |
|---|---|
| Parser, leak guard, corpus (1,765 chunks), BM25 retrieval, ledger, context, generator | in, with tests |
| Service, `/api/help`, practice UI help panel, scripted e2e | in; container smoke not yet run |
| Evaluation harness and gates (`evals/help/`) | in; owner-reviewed sets await Codex disposition |
| Burst tool help mode (`submit_burst.py --mode help`) | in, with tests |
| Preliminary local mixed-load run | recorded, [not the gate](../../../../../ops/host-sizing-c1.md) |
| Ops docs: key, help off, guard memory, security page | [runbook C1](../../../../../ops/runbook-c1.md), [security](../../../../../ops/security.md) |

## Owner checklist (in order)

1. Review 66 cases and 40 queries; set `reviewed_by: tg` ([step 6](../../../../../../evals/help/README.md)).
   **Done 2026-11-05** (all 66 cases, 40 queries); label changes and the how-to rule are in the
   [label review](../../../../../reviews/2026-11-05-c1-label-review/README.md), pending Codex review.
2. Approve the 18 confusion labels (6 per topic, 2026-10-28), the 4 rewritten misconception notes (error-only wording:
   3.6-221, 3.6-229, 3.6-253 and the `sinx2` choice), the help panel copy, the **provider
   disclosure wording** (practice page, `#help-disclosure`; spec 09 requires it) and the hint
   level and mistake-type wording (R35: `LEVEL_RULES` in `help/prompts.py`,
   `MISTAKE_DESCRIPTIONS` in `help/generator.py`, `prompts/v1/hint_choice.md`).
   **Approved 2026-11-05** with R37 (level 0 asks, then names), label #7 reworded, two-click
   Show answer: [step 2 brief](../../../../../reviews/2026-11-05-c1-label-review/02-step2-brief.md).
3. Paid dev run with `--max-usd 4`; blind audit; recompute. Tariffs rechecked by Thomas on the
   Anthropic pricing page 2026-11-05 (C-O5): Haiku 5.5 $0.10/$0.50 (prompts ≤100k), Sonnet 5.5
   $2/$10 per MTok, matching `help_config.json`; judge is Sonnet 5.5. Credit $15.
   Run 1 `20261105-222204-dev` (config c1-1): $1.06, 0 leaks, neither model passes; R38 raises
   the output cap (c1-2) and run 2 follows. Audit run 2, not run 1.
4. **Retrieval gate decision (2026-11-05, before the holdout):** keep the holdout Recall@6
   gate at 0.80. Disclose the development Recall@6 of 0.7738 after relabeling as near the gate; it does not
   justify lowering a predeclared threshold. Report the one-shot holdout result and any
   missed gate plainly. A reviewer scored the draft holdout labels at 0.576 on BM25 before
   the labeling policy; no holdout label was edited in response (ledger ruling on retrieval
   fixes).
5. One-shot holdout; write the chosen model into `help_config.json`. Holdout cap: credit
   minus the `--spent` total minus at least $0.30 ([eval README](../../../../../../evals/help/README.md), step 9).
6. `E2E=1 bash tests/container/smoke.sh`, then the container mixed-load measurement; apply
   the headroom rule; move to 2 GB if it fails (approved 2026-10-26).
7. Gate check (all true, links added here): CI green (Python, Node, container e2e);
   `content_check` and verifier gates unchanged; holdout gates pass; mixed-load recorded;
   demo recorded (one cited hint on a wrong derivative, one abstention out of book).
8. Deploy per the runbook, set the key, check `/readyz`, try one hint and one abstention live.
9. Then update `handoff.md` and the open register (C-O3 result, C-O5 done, C-P1/C-P2 closed)
   and commit `docs: C1 released`.

## Gate evidence (fill in at release)

| Gate | Link or result |
|---|---|
| Code review fixes | all nine closed locally; see debugging fixes and validation |
| CI green | pending |
| Verifier and `content_check` unchanged | pending |
| Holdout gates | pending (dev Recall@6 0.7738 after relabeling) |
| Container mixed-load and memory | pending (preliminary only) |
| Demo | pending |
| Provider disclosure wording approved | approved by Thomas 2026-11-05 |
