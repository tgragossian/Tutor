# Load-validation findings and release limits

[Review](README.md) · [Load probe](repro_load.py) · [Host sizing](../../ops/host-sizing.md)

## B-R4 (P2): fail the load measurement when requests fail

Owners: [submit_burst.py](../../../tools/load/submit_burst.py), lines 76–86 and 202–206;
[measure.sh](../../../tools/load/measure.sh), line 29.

`summarize()` treats every HTTP 200/503 as expected, regardless of the reported outcome.
Sixteen `503 database_busy` replies yield **zero unexpected replies** and a successful CLI
exit. Those are failed database writes, not the expected `503 verifier_busy` backpressure.
Likewise, status 200 alone does not establish the intended answer was actually graded.

The shell wrapper separately runs the burst with `|| true`, discarding even an explicitly
failing CLI exit while continuing to print plausible memory measurements. A run with no
successful verification could therefore appear usable for sizing. The pure-function probe
reproduces the database-error misclassification; shell propagation was established by inspection.

Fix direction: validate expected outcome/error pairs (and retain verdict reasons), require
actual graded work for a sizing run, and report transport failures explicitly. Preserve the
burst's exit code through sampling/cleanup and return it after printing diagnostics.
Add tests for database busy, internal-error/format outcomes, zero successful grades and
nonzero burst exit propagation. Memory reports can still be printed for failed runs.

## Existing evidence remains dated and valid for its stated scope

The recorded 2026-10-22 host run explicitly has **8 incorrect grades and 8 verifier_busy**
replies. It does not exhibit this defect; do not discard it or invent a new production run.
Thomas's 1 GB / one worker / 384 MB cap exception remains in force, with sizing revisited in C.

Compose storage/migration ordering, non-root image ownership and the container e2e wiring
are implemented. This review did not execute Docker or measure Linux/host memory.
`/readyz` checks `SELECT 1`, not schema version; retain the mandatory migration step.
Offline `content_check` still has no hard subprocess deadline (already tracked); the 22
current problems passed locally. Keep that follow-up distinct from B-R4.
