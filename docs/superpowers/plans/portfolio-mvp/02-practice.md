# B — one complete practice loop

[Plan index](README.md) · Budget target: 30 hours.

## Build sequence

1. Implement allowlisted translation and domain-aware checks for the narrow answer types.
2. Run all mathematical work in a bounded worker with a bounded request queue.
3. Add migrations, accounts and session-item/submission persistence.
4. Connect one topic picker and MathLive form to submit, feedback, retry and advance.
5. Expand to 20–30 reviewed problems; publish the working loop.

Reuse original Tasks 3–5, 7–9, 12 and 15–19 only after applying the review corrections.
Implement transactions in application services shared by JSON and HTML routes.
Use textbook order initially; save enough history to evaluate a later selection policy.

## Required behaviors

- Use the shared domain default; ignore only proven removable holes, with a strict override.
- Poles, branch mismatches and unproved domain coverage never disappear through cancellation.
- Numeric sample agreement alone never marks an exact symbolic answer correct.
- Incorrect, unsupported and infrastructure failure are distinct internal reasons.
- An inconclusive answer does not lower mastery or trap the student on an item.
- A retry belongs to its presentation; a later revisit gets a new presentation.
- Duplicate submission IDs have one persisted outcome.
- Another user's session cannot be read, advanced, graded or revealed.
- Page refresh does not reset item timing or reveal private answer fields.

Numeric/choice checks avoid unnecessary general symbolic machinery.
Keep the UI simple: problem, answer editor, feedback, next/skip, and source attribution.
Use a normal page/form flow or a deliberate HTMX HTML-fragment adapter.

## Verification gate

- At least 80 reviewed regression/adversarial cases before the first working demo.
- Every false accept in those cases blocks the release.
- Report correct-input coverage; do not “pass” by abstaining on everything.
- Test same-pool recovery after timeout/death and bounded behavior under concurrent load.
- Test simultaneous duplicate submissions, stale item revisions and exhausted items.
- Browser smoke: register, select topic, submit, retry/advance and revisit history.
- No need for tests that merely assert a version string or README section headings.

## Demonstration

A reviewer can complete a problem at the deployed URL and inspect documented API shapes.
Record current supported expressions and limitations next to the evaluation results.
Introduce tutoring hints in milestone C using this same problem/attempt context.
Retain broader modes and implicit-topic support in the [ordered queue](05-expansion-queue.md).
