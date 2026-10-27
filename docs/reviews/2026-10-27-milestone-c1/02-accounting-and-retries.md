# C1 review: accounting and retries

[Review index](README.md) · [Validation](04-validation-and-next-steps.md)

## C1-R3 (P1): preserve cost after dispatch

- Evidence: `src/mathtutor/help/generator.py:182-195`, `help/pipeline.py:274-283,189-201`,
  `help/service.py:303-318`.
- The pipeline records a call only after `generate` returns, or when it raises the specific
  `GeneratorError` type. An unexpected exception during response decoding reaches the outer
  catch with no call record. `_settle` interprets that absence as "reserved, never sent"
  and settles the reservation to zero, even though the provider was contacted.
- Reproduction: `test_reply_decode_error_retains_spend_reservation` in
  [Python probes](test_review_probes.py). A fake Messages client returns malformed `content`
  after one dispatch. The real `ClaudeGenerator` raises `TypeError`; the service responds
  `unavailable`, with a usage entry in `state='settled'`, `settled_micros=0`.
  This simulates a malformed provider response; no real billing event was generated.
- Consequence: possibly paid work disappears from the budget, so future admissions can
  spend the same reservation again. Evaluation also derives costs from the lost call list.
- Fix: distinguish reserved-but-not-dispatched from dispatched-with-unknown-outcome. Record
  dispatch before entering provider code, retain conservative accounting on unexpected errors,
  and replace that record with actual usage when available. Release zero only for a proven
  pre-dispatch failure or a provider failure whose billing classification is established.
  Review the generic `AnthropicError` mapping at `generator.py:178-179` under the same rule.
- Acceptance: malformed content/usage and SDK response-validation failures retain uncertain
  cost; a prompt-budget failure before dispatch still releases its reservation. Test repair
  calls, replay, evaluation accounting and persistence across restart. Never expose raw errors.

## C1-R8 (P2): retain the ID for an ambiguous help request

- Evidence: `src/mathtutor/web/static/practice.js:310-339,355-361`.
  `askHelp` generates a new UUID for every click. A transport error, unreadable response,
  or still-pending result clears `helpBusy` and invites retry without retaining that UUID.
- If the first request committed a hint before its response was lost, retry is admitted
  as a new paid request. It advances the hint level again and can skip the hint the student
  never saw. Server idempotency cannot help because the browser changed the identifier.
- Reproduction: [Node probe](review_ui_probe.mjs) calls the actual page controller twice
  with a dropped response. The retry sends `uuid-2`, while replay requires `uuid-1`.
- Fix: retain the unresolved request's UUID and payload for retry/poll until a definitive
  response, explicit cancellation policy, or item/revision change. Do not reuse the UUID
  with a different help type/confusion. Make unresolved state and retry behavior explicit.
- Acceptance: simulate a server-committed/lost response, then retry; provider call count,
  hint level and help sequence advance once, and the original hint is shown. Include two
  pending replies, malformed JSON, item changes and concurrent tabs. A `pending` reply naming
  another request must not silently turn a poll into a new generation after it finishes.

## C1-R9 (P1): persist evaluation spend before and during calls

- Evidence: `src/mathtutor/help/eval/run.py:258-286,512-563`, `eval/report.py:409-415`.
  `SpendCounter` is memory-only. `_execute` writes `run.json` only after all cases finish;
  its `finally` closes pools without persisting partial accounting. A holdout's earlier
  `started.json` stores commit metadata, not spend; a dev run has no early artifact at all.
- Reproduction: `test_interrupted_dev_run_preserves_cost` uses synthetic reviewed dev data,
  a scripted provider and fake pools, then raises `KeyboardInterrupt` after the first case.
  One call incurred 350 micro-USD in the in-memory counter; no `run.json` was written.
  The test substitutes a dummy key-variable name and never reads or sets the actual key.
- The documented next-run credit formula sums `results/*/run.json`. It therefore omits
  interrupted work and can overstate the budget available for the one-shot holdout.
  The per-run cap still works during normal execution; the missing guarantee is recovery.
- Fix: persist reservations before every help/judge dispatch and settle usage incrementally;
  retain uncertain worst-case costs after interruption. Derive next-run credit from those
  durable records and provider reconciliation, including incomplete runs. Reject reused run
  IDs that could overwrite previous accounting. Amend R26's "None" risk disposition.
- Acceptance: interrupt after admission, after provider success and during judging; a fresh
  process still counts settled/uncertain costs. Final summary generation is not required
  to preserve spend. Keep the real holdout untouched while testing these transitions.
