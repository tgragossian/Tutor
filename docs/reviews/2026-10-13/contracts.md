# Session, UI and API findings

[Review index](README.md)

## C1 — P1: introduce an item-presentation record

[Task 16](../../superpowers/plans/core-practice-loop/tasks/16-session-and-attempt-api.md)
asks whether an item is finished using attempts_on_item; the schema has no
presentation identity. A previously exhausted item selected again by Task 14 can
already appear finished. First attempt, retry count and elapsed time are ambiguous.

Add session_items: id, session_id, item_id, item_version, sequence, phase, state,
served_at, completed_at, revealed_at. Attempts reference session_item_id.
Define first attempt per presentation, and separately retain prior exposure for mastery.
Specify how unanswered, skipped, uncertain and revealed items affect recommendations.
Use stable topic/content versions so historical attempts survive later content edits.

## C2 — P1: make submission atomic and repeatable

Sequential double-submit tests do not cover two requests passing the same state check.
Use submission_id with a uniqueness constraint and an item state/revision check.
Reserve/validate the presentation, grade outside the SQLite write transaction, then
recheck its revision and commit the result once in a short transaction.
Replays of the same submission return its stored result; conflicting submissions
receive a defined conflict response. Test overlapping calls, not just sequential ones.

GET /next currently writes state and timestamps. Make GET read the current presentation;
use POST to advance, skip or reveal. Refresh must not reset time-on-item.
Persist a diagnostic plan if that feature is added later; do not reconstruct it from
timestamps and a content bank that may have changed.

## C3 — P1: define the learning interaction as a state machine

After the third wrong attempt, Task 16 marks an item finished, while reveal is still
available. Specify active -> awaiting_reveal_or_advance -> completed.
Model reveal as an event, not an edit to a historical answer.
Allow an explicit skip/advance for unable_to_verify; it is neither wrong nor a
mastery observation. Decide retry limits separately from infrastructure failures.

Diagnostic verdicts must remain hidden in report/mastery endpoints until completion,
not just in the submit response. Use separate public item DTOs to prevent answer leaks.
Recap/recall needs explicit feedback and completion rules if retained.

## C4 — P1: update the MathLive spike

Task 2 calls getValue('math-json') and requires releases at least two weeks old.
MathLive 0.111.0 removed that output format; the documented replacement parses
mf.getValue() through Compute Engine. Version 0.111.1 fixes rendering XSS issues.
The age rule would exclude that patch on the review date.
[Official changelog](https://github.com/arnog/mathlive/blob/master/CHANGELOG.md)

Pin a patched MathLive release and compatible Compute Engine; record exact versions.
Capture raw input, parser output and rendered round trips before implementing translation.
Use the supported noncanonical parse option, not an assumed ce.canonical assignment.
[Compute Engine documentation](https://cortexjs.io/compute-engine/guides/canonical-form/)
Include malicious rendering inputs, placeholders, C, decimals and function arguments.
The LaTeX fallback changes the wire contract; Task 2 cannot call that interface unchanged.

## C5 — P2: keep adapters explicit

HTMX expects HTML fragments by default; JSON endpoints need fetch or a deliberate adapter.
Let HTML routes and JSON routes call the same application service.
Keep CSRF checks on all cookie-authenticated mutations, including JSON requests.
Escape user text, sanitize rendered Markdown and restrict URLs and math rendering.
Define cookie expiry, logout behavior and single-process rate-limiter assumptions.
Do not log passwords, session tokens or full tutor conversations by default.
