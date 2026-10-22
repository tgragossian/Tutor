# Host memory sizing (milestone B)

[Production host](host.md) · [Runbook: measure memory](runbook.md#measure-memory-load-burst)

Spec 09 rule: workers × per-worker memory cap + app + Caddy + OS must stay within 85% of RAM.
On the 1 GB bundle (909 MiB usable) that budget is about 773 MiB. If no pool setting fits,
the fallback is the 2 GB bundle (Thomas decides).

## Idle (2026-10-21, after the milestone B deploy)

App + worker 135 MiB, Caddy 17 MiB, about 386 MiB available (from the handoff).

## Load burst

Not run yet. Command: `bash tools/load/measure.sh https://tutor.thomasgragossian.dev`
(16 users, dev case `d-181-07`, the slowest live case).

A local dry run on Windows (2026-10-22, 1 worker, not the server) graded 9 of 16 and returned
`verifier_busy` for 7, with p50 282 ms and max 1975 ms, which matches the queue of 8 and
2-second queue wait.

## Decision

Pending the burst numbers: keep `MATHTUTOR_POOL_SIZE=1` / `MATHTUTOR_POOL_MEMORY_MB=384`, or
change them in `deploy/.env`, with the arithmetic recorded here.
