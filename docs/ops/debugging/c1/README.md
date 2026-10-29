# C1 help debugging

[Debugging tree](../README.md) · [C1 status](../../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md)

This maps the implemented `milestone-c1` worktree. C1 is not released. Run commands from
that worktree; file names in the child tables are relative to `src/mathtutor/`.

```text
C1 help
  01-generation.md   startup -> context/retrieval -> provider -> parser/guard -> display
  02-state-cost.md   request identity -> admission -> hint state -> finalize -> usage
  03-evaluation.md   dataset -> partition claim -> spend -> judge/audit -> gates
```

| Symptom | Start here |
|---|---|
| Healthy app, missing buttons, unavailable help | [Generation and startup](01-generation.md) |
| Wrong passage, broken citation, answer leak, excessive blocks | [Generation and guard](01-generation.md) |
| Hint level jumps, duplicate request, stale/deleted text | [State and cost](02-state-cost.md) |
| Missing charge, quota reset, uncertain reservation | [State and cost](02-state-cost.md) |
| Holdout reuse, missing baseline score, interrupted evaluation | [Evaluation](03-evaluation.md) |
| Container memory, key configuration or rollout | [C1 runbook](../../runbook-c1.md) |

The [current review](../../../reviews/2026-10-27-milestone-c1/11-debugging-fixes.md) owns defect
status; these pages own navigation. Passing a focused test does not establish release readiness.
Use scripted generators and synthetic evaluation cases for debugging. Keep the real holdout
out of diagnosis, and keep student/provider text and credentials out of logs.
