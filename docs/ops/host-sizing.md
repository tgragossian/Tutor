# Host memory sizing (milestone B)

[Production host](host.md) · [Runbook: measure memory](runbook.md#measure-memory-load-burst)

Spec 09 rule: workers × per-worker memory cap + app + Caddy + OS must stay within 85% of RAM.
On the 1 GB bundle (909 MiB usable) that budget is about 773 MiB. If no pool setting fits,
the fallback is the 2 GB bundle (Thomas decides).

## Idle (2026-10-21, after the milestone B deploy)

App + worker 135 MiB, Caddy 17 MiB, about 386 MiB available (from the handoff).

## Load burst (2026-10-22, on the host, 1 worker, cap 384 MB)

`bash tools/load/measure.sh https://tutor.thomasgragossian.dev`: 16 users, dev case `d-181-07`.

| Measure | Value |
|---|---|
| Replies | 8 graded (`incorrect`, as labelled), 8 `verifier_busy` (queue of 8 full) |
| Latency | p50 636 ms, p95 2370 ms, max 2370 ms; burst 2374 ms |
| Container peak (docker stats) | app 185.2 MiB, Caddy 28.5 MiB |
| Peak RSS (VmHWM) | app 145 MiB; verifier worker 72 MiB; 16 MiB process (likely multiprocessing's resource tracker) |
| `free -m` before → after | used 551 → 585, available 358 → 324, swap used 118 → 144 |
| Lowest available during the run | 281 MiB |

OS, Docker daemon and agents: used 551 − containers 151 ≈ **400 MiB**.

## Arithmetic (spec 09 / task 16 rule: ≤ 85% of 909 MiB ≈ 773 MiB)

- **Worst case with the cap (the rule):** 1 × 384 + app 145 + tracker 16 + Caddy 28 + OS 400
  = **973 MiB**, above the budget by about 200 MiB and above physical RAM. It does not fit.
- **To fit on 1 GB** the cap would have to be ≤ about 184 MB. `RLIMIT_AS` limits *virtual*
  memory, which for a Python + SymPy worker is well above its 72 MiB RSS, so a cap that low
  would probably stop the worker from starting. Check the worker's `VmPeak` before trying it.
- **Measured reality:** the worker never got near the cap; at least 281 MiB stayed available
  during the burst. A second worker is out either way.

## Decision (Thomas)

Keep `MATHTUTOR_POOL_SIZE=1`, `MATHTUTOR_POOL_MEMORY_MB=384` (the defaults) for now. The
plan's worst-case rule fails on 1 GB, so the plan says to propose the **2 GB bundle**. The
alternative is to accept 1 GB with the measured headroom and 1 GB swap as the safety margin.
That relaxes the plan's rule, so it is Thomas's call and must be recorded here if chosen.
