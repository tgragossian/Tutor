# Reviewed areas with no new finding

[Review](README.md) · [Validation and limits](04-validation.md)

These are bounded review conclusions, not guarantees. Unrelated deferred observations stay
in [follow-ups](../../superpowers/plans/portfolio-mvp/milestone-b/05-follow-ups.md).

## Verifier and evaluation (tasks 1–9)

- Traced exact JSON decimals, iterative structure bounds, prechecks and allowlisted translation.
  Raw-tree constraints survive cancellation; computed exponents are bounded before proof.
- Inspected symbolic proof/domain ordering, exact rational/trig violation sets, conservative
  fallback and interval-based refutation/rounding. No new false accept found in this pass.
- Inspected worker-only imports, process teardown/replacement, bounded queue and default
  deadline. Tests cover process isolation and same-pool recovery; Windows cannot test RLIMIT_AS.
  Synchronous replacement delay is relevant to B-R5 and remains a deferred pool concern.
- Reviewed evaluation label/category/reviewer gates, empty-set rejection and unsupported
  acceptance checks. Fresh dev/generated CLI gates pass with complete agreement.
- Content compiler reproduction is byte-identical. All 22 approved problems pass offline
  validation; schema/review/source filtering and private-answer DTO boundaries remain enforced.
  This is not another human mathematical review of the content labels.

## Application and web (tasks 10–15)

- Rechecked B-A1: actions carry presentation ID plus revision; duplicate/racing/stale actions
  are covered by normal regressions. One browser mutation at a time remains implemented.
- Rechecked B-A2: raw submit JSON depth is scanned before parsing, and recursion failures
  become controlled validation errors. Body and MathJSON bounds still run before the pool.
- Rechecked B-A3: reads use deferred transactions; writes use BEGIN IMMEDIATE. Authentication
  and lock-contention regressions pass, with retryable API errors and post-lock recovery.
- Rechecked B-A4: persisted problem snapshots drive old rendering/grading/reveal; new content
  versions apply to new presentations. Snapshot tests include edited and removed problems.
- Rechecked B-A5: late format results validate current presentation/revision/state; the page
  serializes actions. B-R1 concerns retained payloads after retries, a different path.
- Ownership, server-side session expiry/logout, CSRF, cookie flags, rate limits and answer-leak
  tests pass. Inspected selection/history and the A19–A21 UI changes without a new finding.
- Normal reservation and result transactions remain separate from verification. The new
  recovery findings concern aged concurrent reservations, beyond the normal race coverage.

## Release (task 16)

- Inspected Docker's non-root runtime, `/data` ownership and persistent compose volume;
  migrations complete before app startup. Schema migration tests pass locally.
- CI includes Python/Node gates and browser e2e against the production image through the
  container smoke script. Uvicorn access logging is disabled in that image.
- Settings expose worker count/memory cap; verifier limits and evaluation results are published.
- Existing deployment and host measurements are reported evidence, not rerun here.
  Keep the recorded host-sizing exception and outstanding hours gate visible.
