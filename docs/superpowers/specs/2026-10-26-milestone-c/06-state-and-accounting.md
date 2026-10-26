# C design 6: help state, deletion and accounting

[C design](README.md) · [Review rationale](../../../reviews/2026-10-26-milestone-c/02-state-and-cost.md)

Review amendment, 2026-10-26. These are required new interfaces, not existing B behavior.

## Request lifecycle

1. Authenticate, check CSRF, field bounds and ownership of the current presentation.
   Validate revision, help-type eligibility and a server-owned confusion ID before inference.
2. Bind `help_request_id` to user + canonical payload + item/problem version. Reject reuse
   with different payload. A duplicate pending request returns pending; completed requests
   replay only while their presentation and privacy epoch remain valid.
3. In a short transaction, reserve rate allowance, worst-case spend and a hint-level slot.
   Serialize help on one item. Store the context cutoff and privacy epoch. Do not alter tries,
   verdicts or `SessionItem.revision`; help state has its own sequence.
4. Release the transaction before retrieval, provider, parsing or worker calls.
5. Recheck ownership, current item/revision, deletion epoch and help sequence before finalizing.
   Discard stale text; retain content-free usage. The browser also rejects stale responses.
6. Increment the hint ladder only for an accepted generated hint, once, capped at 3.
   Feedback/explain, failure, blocked fallback and replay do not advance it.
7. Return a terminal status, request ID, item ID/revision, help sequence and validated payload.
   A crash after dispatch is an uncertain outcome, never automatic permission to call again.

Help is available on active/exhausted items; after correct, reveal or departure, close the
request and clear the help panel. Feedback requires the latest consumed verdict to be wrong.
Do not reinterpret `unable_to_verify` or a format issue as a mathematical misconception.
The current C2 box is item-scoped; independent chat is outside C2's contract.

## Persistence and privacy

- B's `clear_history()` currently hides sessions and retains attempts for progress.
  C adds actual removal of help text/questions and C3 own problems/associated private content;
  the UI explains that bank progress still remains. Do not claim B already deletes everything.
- Clear/delete increments a privacy epoch and invalidates pending jobs and replay payloads.
  No delayed provider/solver completion may recreate deleted text. Cover reload and retries.
- Store confirmed own-problem versions separately; deletion removes their statements,
  answers, attempts and help payloads. No own-problem copy survives in a bank snapshot.
- Keep billing/rate records without questions, responses, source text or uploaded bytes.
  Clearing history must not reset spend or rate limits. Backups and provider retention need
  explicit retention windows and restore-time deletion handling before C3 release (C-P3).
- General request/error logs omit student text, raw provider bodies and secrets. Evaluation
  exports use reviewed cases; private live text is not automatically training/evaluation data.

## Spend and retries

The $15/month value is the initial app admission budget, in UTC calendar months. Before each
provider attempt, atomically ensure settled + reserved + new worst-case cost fits. Reserve
bounded input, output and any billable reasoning/cache/image tokens using a versioned tariff.
Reconcile actual usage; charge retries, blocked responses, intake and any shared-account evals.
Unknown usage stays reserved conservatively across crashes/month boundaries until reconciled.
Do not hold DB locks during calls or compute spend from deletable help events.
Per-student limits are safety ceilings, not guaranteed allowances once the shared budget is spent.

At most two generator calls per logical help request, across all repair reasons combined.
Explicitly disable SDK retries; only the service owns retries, deadlines and cost reservations.
Do not automatically resend an ambiguous transport timeout. Provider console controls are a
backstop, not proof that the application has a race-free billing cap. Keep auto-reload off.

## Bounds and follow-up evidence

The initial 15 s help deadline covers the whole request: queue, retrieval, provider attempts,
parsing and guarding. Child calls get only remaining time. Set total input tokens/bytes,
context/math lengths and global admission limits in C-P1; six chunks alone is not a bound.
Test help plus grading together; preserve grading capacity within the measured host budget.
If retrieval/provider is unavailable, disable help without failing core practice readiness.

Record delivery eligibility time and next submission's reservation time/ID. Link only an
attempt started after eligible help on the same item. Group multiple hints as one episode;
report assistance exposure, not demonstrated learning. An optional client display receipt
may distinguish delivery from rendering but cannot establish that the student read the hint.
