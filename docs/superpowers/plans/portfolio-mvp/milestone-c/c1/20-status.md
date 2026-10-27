# C1 status: pre-release (2026-10-27)

[C1 plan](README.md) · [Gates](02-gates.md) · [Runbook C1](../../../../../ops/runbook-c1.md) ·
[Open register](../03-open-decisions.md)

Tasks 1 to 15 are implemented on branch `milestone-c1`; reviewed by subagent per task. The
branch is **not released**: nothing is deployed, no holdout has run and no key is on the host.
[Codex review](../../../../../reviews/2026-10-27-milestone-c1/README.md) of `3be5808` found nine
open issues (five P1 blockers). Claude must fix them before the paid/release steps below.
The [review checklist](../../../../../reviews/2026-10-27-milestone-c1/04-validation-and-next-steps.md)
owns fix order and fresh local evidence; the owner steps still need key, credit, Docker and host.

## Done

| Area | State |
|---|---|
| Parser, leak guard, corpus (1,765 chunks), BM25 retrieval, ledger, context, generator | in, with tests |
| Service, `/api/help`, practice UI help panel, scripted e2e | in; container smoke not yet run |
| Evaluation harness and gates (`evals/help/`) | in; sets are drafts awaiting review |
| Burst tool help mode (`submit_burst.py --mode help`) | in, with tests |
| Preliminary local mixed-load run | recorded, [not the gate](../../../../../ops/host-sizing-c1.md) |
| Ops docs: key, help off, guard memory, security page | [runbook C1](../../../../../ops/runbook-c1.md), [security](../../../../../ops/security.md) |

## Owner checklist (in order)

1. Review 60 cases and 40 queries; set `reviewed_by: tg` ([step 6](../../../../../../evals/help/README.md)).
2. Approve the 12 confusion labels, the 4 rewritten misconception notes (error-only wording:
   3.6-221, 3.6-229, 3.6-253 and the `sinx2` choice), the help panel copy and the **provider
   disclosure wording** (practice page, `#help-disclosure`; spec 09 requires it).
3. Paid dev run with `--max-usd 4`; blind audit; recompute.
4. **Decide on the retrieval gate before the holdout:** dev Recall@6 0.79 is below the 0.80
   gate (disclosure: a reviewer scored the draft holdout labels at 0.576 on BM25 before the
   labeling policy; no holdout label was edited in response; ledger ruling on retrieval fixes).
5. One-shot holdout; write the chosen model into `help_config.json`. Holdout cap: credit
   minus the sum of earlier `spent_micros` minus at least $0.30 ([eval README](../../../../../../evals/help/README.md), step 9).
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
| Code review fixes | pending: C1-R1 through C1-R9; P1 blocks release |
| CI green | pending |
| Verifier and `content_check` unchanged | pending |
| Holdout gates | pending (dev Recall@6 0.79) |
| Container mixed-load and memory | pending (preliminary only) |
| Demo | pending |
| Provider disclosure wording approved | pending (implemented, wording awaits Thomas) |
