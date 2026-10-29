# C1 review: code close-out and release handoff

[Review index](README.md) · [Recheck](07-recheck.md) · [Dispositions](05-dispositions.md)

Updated 2026-10-28 after Codex debugged the R4/R7 follow-ups on `b16a206`.
[Local fixes and validation](11-debugging-fixes.md) supersede the intermediate recheck queue.

## Completed in the documentation continuation

- Recorded individual verdicts: all nine original findings closed in local code.
- Reviewed R35/R36 and recorded their scope and limits.
- Updated handoff, review/status/rulings, evaluation guidance and operational navigation.
- Added a modular [C1 debugging tree](../../ops/debugging/c1/README.md) with source/test owners.
- Recorded [fresh validation](10-recheck-validation.md), separating environment failures,
  known-defect probes, passing regressions and unrun release gates.

## Completed debugging pass

1. R4: partition claims precede retrieval scores; retrieval-only holdout runs are refused.
2. R7: baseline mode survives judge/audit/recompute; production citations remain mandatory.
3. Added normal regressions; the two saved follow-up probes now pass without xfails.
4. Retired original probes to navigation stubs; no fixed finding retains a strict xfail/TODO.
5. Recorded [validation](11-debugging-fixes.md) separately from owner/provider/container gates.

## Remaining work

Carry the C1 fixes into C2, then review its plan against the spec and implementation.
C2 Q1–Q9 are already decided by Thomas in `milestone-c2`; do not ask those questions again.
No C2 plan-review completion is claimed here. Preserve the C1 owner release checklist:
case/copy review, fixed gates, paid development comparison, holdout, container smoke/memory
and live deployment verification. Documentation closure alone is not release approval.
