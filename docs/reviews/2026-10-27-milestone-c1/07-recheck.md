# C1 pre-fix recheck — 2026-10-28

[Review index](README.md) · [Dispositions](05-dispositions.md) · [Original evidence](04-validation-and-next-steps.md)

Codex rechecked `milestone-c1` at `b16a206`, including the fixes after the original
`3be5808` review and R35/R36. This page records the pre-fix verdicts; pages 01–04 preserve
the original defects and evidence. Subsequent [debugging fixes](11-debugging-fixes.md) close R4/R7;
the verdicts and failed-probe results below describe the earlier unchanged source.

## Outcome

Seven original findings close at the source/regression level: C1-R1/R2/R3/R5/R6/R8/R9.
C1-R4 (P1) and C1-R7 (P2) reopen; see [evaluation follow-ups](08-evaluation-follow-ups.md).
Paid comparison/release remains blocked; C2 implementation still waits for C1 closure.
Container packaging validation remains an independent release gate after R1's code fix.

| Finding | Verdict | Evidence and remaining limit |
|---|---|---|
| C1-R1 | Closed in code | Dockerfile copies help configuration; `test_dockerfile.py` reconstructs the runtime layout. Actual image smoke pending. |
| C1-R2 | Closed for the reported bypass | Real-checker cancellation/numeric/notation regressions exercise substituted foreign atoms. D1 is bounded heuristic coverage, not proof for every foreign expression. |
| C1-R3 | Closed | Dispatch is recorded before generation; malformed responses and repair crashes retain uncertain spend; pre-dispatch failures release zero. |
| C1-R4 | Reopened, P1 | Retrieval metrics are exposed before partition claims; retrieval-only returns without checking/claiming use. |
| C1-R5 | Closed | Guard clearance and pipeline delivery recheck deadlines. Blocking worker duration is still not a hard end-to-end latency guarantee. |
| C1-R6 | Closed | Feedback query uses the latest wrong attempt; six context/query cases cover it. |
| C1-R7 | Reopened, P2 | Uncited baseline calls the generator but its output shape is absent from judge ingestion. |
| C1-R8 | Closed | Node tests retain unresolved request IDs across lost/malformed replies, pending responses and retries. Real two-tab browser check pending. |
| C1-R9 | Closed | Fsynced reserve/settle journal preserves interrupted help/judge spend; `--spent` includes uncertain reservations. Provider reconciliation remains manual. |

## Evidence navigation

- [Validation](10-recheck-validation.md): fresh commands, results and environment limits.
- [Evaluation follow-ups](08-evaluation-follow-ups.md): two synthetic reproductions and fix acceptance.
- [R35/R36](09-hint-and-prompt-review.md): hint-state and prompt-provenance review.
- [Debugging tree](../../ops/debugging/c1/README.md): source ownership and focused checks.

The saved [recheck probes](test_recheck_probes.py) were run with `--runxfail`:
both fail at their intended assertions. With strict xfail enabled these are known defects,
not successful regressions. They use temporary synthetic partitions and scripted providers.

## Next implementation pass

1. Fix C1-R4 before exposing any holdout metrics; preserve existing consumed-set claims.
2. Fix C1-R7 through judge, audit and recompute, including R35's classifying hint shape.
3. Add passing regressions under `tests/`, then remove the matching recheck xfail markers.
4. Retire or rewrite the original review probes: their old Dockerfile, fake-pool and
   `run.json` assumptions are superseded. Use the regression owners in dispositions.
5. Recheck both findings, then follow the [owner gates](../../superpowers/plans/portfolio-mvp/milestone-c/c1/20-status.md).
   No paid call, real holdout, container run or deployment was performed in this recheck.
