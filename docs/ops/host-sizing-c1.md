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
