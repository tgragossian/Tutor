# Milestone B whole-branch review — 2026-10-22

[Reviews](../README.md) · [Handoff](../../../handoff.md) · [Status](../../superpowers/plans/portfolio-mvp/milestone-b/03-execution-status.md)

Reviewed `main` and `milestone-b` at **15169a2** (identical commits).
Scope: tasks 1–16, prior review fixes, verifier/evaluation, application/store/web and release wiring.
Production implementation and content are unchanged. New probes live beside this review,
outside ordinary test collection; they assert desired behavior and currently fail.

## Findings, in repair order

| ID | Priority | Finding | Detail |
|---|---|---|---|
| B-R5 | P1 | A busy orphan replay can delete live work and attach its result to another user's submission | [Recovery](01-recovery.md#b-r5-p1-reservation-deletion-and-row-id-reuse) |
| B-R1 | P2 | Editing after exhausted retries silently resends the previous answer | [UI](02-ui-and-timing.md#b-r1-p2-retry-the-answer-the-student-can-see) |
| B-R2 | P2 | Orphan recovery trusts the retry's newer revision and applies an obsolete answer | [Recovery](01-recovery.md#b-r2-p2-preserve-the-original-reservation-revision) |
| B-R3 | P2 | Answer-time history includes verifier and recovery delay | [Timing](02-ui-and-timing.md#b-r3-p2-stop-student-timing-at-submission) |
| B-R4 | P2 | Load validation accepts database failures; its wrapper discards failure status | [Release](03-release.md) |

All five are open. B-R5 is a data-integrity issue requiring prompt repair; resolve the
findings before closing B. No production incident is asserted: reproductions use local
temporary databases or stubbed transport. B-R2 exposes a problem in existing ruling A14,
not a failure to implement that ruling. The recovery fix must amend the ruling explicitly.

## Evidence

- [Validation](04-validation.md): 890 Python tests passed, one Linux-only skip; 19 Node tests;
  lint/format/types and all 22 content checks passed; compiled content reproduced exactly.
- Both verifier CLI gates pass: dev agreement 136/136 and generated agreement 94/94, FA 0.
- Four Python probe failures and one JavaScript controller probe failure establish the findings.
- [Reviewed areas with no new finding](05-covered-areas.md) records coverage and limits.
- Prior B-A1–B-A5 fixes remain implemented; their normal regression tests pass.

## Repair and verification

1. Fix B-R5/B-R2 together: exclusive recovery ownership, stable reservation identity and the
   original revision. Add a new migration; **do not edit deployed migrations 0001/0002**.
2. Fix B-R1 with a clear distinction between retrying an unresolved answer and submitting an
   edit. Preserve idempotency when a response is lost. Add a real browser regression.
3. Fix B-R3 from the original persisted submission time; test delayed and recovered grading.
4. Fix B-R4's outcome validation and shell exit propagation. Keep Thomas's existing host
   sizing exception; the recorded successful burst is not invalidated by this tool defect.
5. Move/adapt probes into normal tests, rerun affected checks and both verifier gates, then
   record fix commits and fresh evidence here. Complete the hours log with Thomas.

Known nested-trig latency and unbounded offline `content_check` remain in
[follow-ups](../../superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md).
