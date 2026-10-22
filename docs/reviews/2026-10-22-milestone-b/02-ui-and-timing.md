# Browser retries and answer timing

[Review](README.md) · [UI probe](repro_ui.mjs) · [Timing probe](repro_state.py)

## B-R1 (P2): retry the answer the student can see

Owner: [practice.js](../../../src/mathtutor/web/static/practice.js), lines 246–295.

`check()` retains `pending` after all four busy/network retries. Its `finally` enables
the controls; editing the MathLive field or selecting another choice does not invalidate
that payload. The next Check uses `pending` without calling `buildAnswer()` again.

Reproduction runs the real controller in Node with stubbed DOM/parser/HTTP:
enter `x`, return four 503 `verifier_busy` replies, edit to `2x`, and click Check again.
The fifth request still contains LaTeX `x`. The server can then grade the old answer and
consume a try while the page displays `2x`. This is separate from B-A5's fixed action ordering.

Fix direction: distinguish an unresolved submission from a new answer. For definite
`verifier_busy` rejection, allow the edit to create a fresh payload. For ambiguous network
failure, reconcile/replay the original UUID before allowing a new mutation, or keep the
editor locked and identify the pending answer. Do not reuse one UUID for changed content,
and do not blindly generate a new UUID after a lost response (which could double-count).

Regression: exhaust busy retries, edit, submit and verify the posted answer/feedback;
repeat with choice answers and a lost successful response. The supplied probe verifies
controller logic only; add a Playwright check with real MathLive when fixing it.

## B-R3 (P2): stop student timing at submission

Owner: [practice.py](../../../src/mathtutor/application/practice.py), line 457.

The stored `seconds_on_item` uses transaction B's `now`, after queueing and grading.
[Session-state spec](../../superpowers/specs/2026-10-13-portfolio-core/06-session-state.md)
defines it as submit time minus `served_at`. A student submitting at 42 seconds with a
7-second grading delay is recorded as taking 49 seconds. The test uses an injected clock
and the normal service submit path; existing tests keep the clock fixed during grading.

An orphan recovered minutes later includes that whole delay, distorting the history used
for future learning/selection analysis. Worker and queue timings are already separate fields.

Fix direction: derive elapsed student time from the original `Submission.created_at` and
the presentation's `served_at`; preserve it across recovery. Keep verifier timings separate.
Regression: delayed pool, database completion delay and much-later orphan recovery must all
retain the original answer time. Do not rewrite historical rows without a deliberate policy.
