# C-R2/C-R3: durable help state and accounting

[Review](README.md) · [State contract](../../superpowers/specs/2026-10-26-milestone-c/06-state-and-accounting.md)

## Evidence

[PracticeService](../../../src/mathtutor/application/practice.py) reserves submissions,
rechecks presentation identity/revision on finalization and hides sessions in `clear_history`.
[Store models](../../../src/mathtutor/store/models.py) retain answers for progress/selection.
[RateLimiter](../../../src/mathtutor/web/security.py) is in process memory. None of these
already implements C's durable spend ledger, deletion semantics or hint-level counter.

## Failure examples

- Double-click Hint at revision 7: two provider calls, duplicate cost and competing levels.
- Skip or submit while help is pending: revision 7 feedback appears beside revision 8's work.
- Clear history during inference: a completed response writes private text back after deletion.
- Two requests see $14.99 spent: both enter, exceeding a $15 cap checked only afterward.
- Delete help events to clear questions: a budget computed from those events resets.
- Twenty 3-second checks plus a retry: the apparent 15-second help timeout is not a total bound.
- A crash after dispatch cannot distinguish “provider billed” from “request never reached it”.

## Amended design

- Use request IDs bound to user, immutable payload, item/version and a privacy epoch.
  Reserve help state and worst-case spend atomically; do network/SymPy work outside SQLite
  write transactions. Revalidate before committing or returning any displayable text.
- Hint level advances only once for an accepted hint; failures, stale responses and replays
  do not increment it. Track help state separately from the grading revision.
- Keep a content-free usage ledger separate from deletable help/question records.
  Rate windows and reservations survive restarts and clear-history operations.
- Charge every provider attempt, including blocked output, retries and upload reading.
  Timeouts/crashes with unknown usage remain conservatively reserved until reconciled.
- One bounded retry budget covers JSON, citation and leak failures; it is not one retry at
  each layer. An end-to-end deadline includes queueing, parsing and guarding.
- Protect grading capacity under mixed help/submission traffic. A new pool consumes memory;
  blindly sharing the existing one-worker pool can make practice unavailable.

## Verification needed

Concurrent duplicate/different-payload requests; crash before/after dispatch; stale submit,
skip and reveal; clear-history/delete during inference; restart near quota; UTC month rollover;
cross-user replay; lost HTTP response; and mixed load showing grading remains usable.

Next-attempt outcomes need request/attempt timing: a submission reserved before help became
available must not be labeled assisted. Server delivery is not proof the student read it.
Several hints before one attempt are one episode, not independent learning observations.
