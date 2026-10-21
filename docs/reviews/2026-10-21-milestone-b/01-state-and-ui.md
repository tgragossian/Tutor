# State and UI findings

[Review index](README.md) · [Reproduction probes](repro_app.py)

## B-A1 (P1): bind actions to a presentation

Owner: [practice.py](../../../src/mathtutor/application/practice.py), lines 228–244;
[ActionRequest](../../../src/mathtutor/web/schemas.py), lines 92–93.

`_act()` loads the latest item and compares only `item_revision`. Each new presentation
starts at revision zero. `ActionRequest` contains no `session_item_id`.
Two sequential `POST /skip` requests with the same original `{item_revision: 0}` both
return 200: first response is presentation 2, second is presentation 3. A duplicate click,
network replay or stale tab can therefore skip a problem the student has never seen.
The browser's `act()` has no in-flight guard, so this is reachable from ordinary UI use.

Fix: require presentation identity with the revision on every action, verify both atomically,
and return 409 for the obsolete target. Update contracts and callers together. A session-wide
monotonic action token is another valid design; disabling buttons alone is insufficient.
Regression: duplicate and concurrent Skip requests, delayed Advance/Reveal and multiple tabs
must never affect the next presentation. Probe: `test_ba1_*`.

## B-A4 (P2): enforce the presentation's content version

Owner: [practice.py](../../../src/mathtutor/application/practice.py), lines 330, 444–448,
483 and 494–496.

Presentation creation saves `content_version`, but `_view()` and grading fetch the current
problem solely by ID. After restarting with an edited bundle, an old presentation renders
new text and can grade against a changed answer while its stored version remains unchanged.
The probe retains version `e52b3bced3bd` in SQLite but renders `<p>Changed after deploy</p>`
from a replacement bundle with a different version. Reproduction changes only in-memory content.
This corrupts attempt provenance and can reject an answer to the pre-deployment statement.

Fix: resolve content by the recorded version, or explicitly invalidate old presentations
when the version differs. Apply the policy to current, submit, replay and reveal; also handle
items removed from the bundle or no longer human-verified. Do not silently relabel old attempts.
Regression: restart with edited statement/answer, changed review status and removed item;
old presentation must retain its content or return a controlled stale/unavailable response.
Probe: `test_ba4_*`; it directly establishes rendering/version mismatch, not a math verdict.

## B-A5 (P2): discard stale format results and order UI mutations

Owner: [practice.py](../../../src/mathtutor/application/practice.py), lines 359–364;
[practice.js](../../../src/mathtutor/web/static/practice.js), lines 214–268.

The format-issue branch releases the reservation, then returns the original item's view
without checking revision/state/current presentation. Skip is available while Check is in
flight; `act()` does not respect `busy`. If Skip renders the next item first, the older
submit response then executes `render(data.item)` and restores the completed item with no actions.
The probe performs Skip during pool submission, returns a FormatIssue and receives a normal
SubmitView instead of StaleItem. The UI consequence follows from unconditional rendering;
this pass did not execute that ordering in a real browser.

Fix: return controlled stale state when a format response's presentation has changed, and
serialize UI mutations or ignore responses from obsolete request generations. Keep server
checks for multi-tab clients. Also cover replays returning views of earlier presentations.
Regression: delayed format response after Skip must leave the next item usable; no tries are
consumed by the format issue. Probe: `test_ba5_*`; add a browser regression for response ordering.
