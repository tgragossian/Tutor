# Host sizing for C1 (help): preliminary

[Host sizing](host-sizing.md) · [Runbook: C1 help](runbook-c1.md)

**Preliminary, Windows, not the release gate.** Docker is not installed on the development
machine, so this is a local uvicorn run (Windows 11, Python 3.12), not the Linux production
image. Windows working-set peaks are not comparable to Linux RSS (VmHWM) and no `RLIMIT_AS`
cap applies. The release number is the container measurement in [runbook C1](runbook-c1.md).

## Setup (2026-10-27)

`MATHTUTOR_ENV=test`, `MATHTUTOR_HELP_GENERATOR=scripted` (no provider call), real corpus
(1,765 chunks) and compiled content, fresh SQLite database, one grading worker and one guard
worker (defaults), no Caddy. Command: `tools/load/submit_burst.py --users 8 --mode help
--help-users 20`: 8 grading submits of the dev case `d-181-07` and 20 hint requests released
at the same moment.

## Results

| Measure | Value |
|---|---|
| Grading replies | 8 of 8 `incorrect` (as labelled); 0 `verifier_busy` |
| Grading latency | p50 1236 ms, p95 2115 ms (B baseline, Linux host, 16 users: p95 2370 ms) |
| Help replies | 5 `delivered`, 15 `unavailable` |
| Help latency | p50 179 ms, p95 260 ms (scripted: no provider wait) |
| Peak working set, web process | 204 MiB (includes the loaded corpus and index) |
| Peak working set, two worker processes | 66 MiB and 62 MiB (grading and guard; not told apart) |
| BM25 index build (1,765 chunks) | 0.44 to 0.56 s |

## Reading the numbers

- Grading was not starved by help traffic. The 15 `unavailable` replies are the designed
  admission limit (`admission.concurrency` 4 help requests in flight per process, extra ones
  answered at once with the fixed unavailable text), not a failure; a real model call takes
  seconds, so the limit also caps provider and guard-pool load. 20 simultaneous hints is
  therefore a stress case: students past the fourth see "unavailable" and can retry.
  The tool counts `unavailable` as an expected help reply and prints the split.
- The two workers together are about 130 MiB of RSS, close to the 72 MiB single-worker figure
  from B. The web process grew from 145 MiB (B, Linux) to 204 MiB here, but the platforms differ.
- Arithmetic on paper, to be replaced by container numbers: 2 workers x 384 MB cap + web
  about 205 + Caddy 28 + OS 400 = about 1,400 MiB worst case against the 773 MiB budget of
  the 1 GB bundle. Measured RSS is far below the caps, as in B. The headroom rule decides;
  if it fails, the move to 2 GB (approved 2026-10-26) is in [runbook C1](runbook-c1.md).

## Container measurement on the host (2026-11-05, image from `8b35584`)

Lightsail 1 GB, 2 vCPU; live app stopped, e2e overlay (scripted help, no provider calls).
`tests/container/smoke.sh` passed on the host (migrations 0004-0005 included); the help browser
test (`HELP_E2E=1 npm run e2e`) passed from a workstation through an SSH tunnel.

| Run | Grading replies | Help replies | Peak app container | Lowest available |
|---|---|---|---|---|
| `8 grading` | 7 incorrect, 1 `verifier_busy`; p95 2156 ms | — | 200 MiB | 248 MiB |
| `8 help 20` (failed run) | 2 incorrect, 6 `verifier_busy`; p95 2555 ms | 4 delivered, 16 unavailable | 245 MiB | 203 MiB |

Per-process peak RSS: web 193 MiB, workers 68 + 68 + 16 MiB; Caddy 14-16 MiB.
- **Memory passes the 85% rule on 1 GB:** at most 909 − 203 = 706 MiB used (78%). C-O3: stay on
  1 GB; 2 GB would not help the finding below, since that bundle also has 2 vCPU.
- **CPU contention fails the mixed burst:** with 20 simultaneous help requests, 6 of 8 grading
  submits got `verifier_busy` (1 of 8 without help). The guard and grading compete for 2 vCPU.
  A 20-hint burst is a stress case for a portfolio site; disclosed, with lowering
  `admission.concurrency` from 4 to 2 as the first mitigation if it appears in real traffic.
