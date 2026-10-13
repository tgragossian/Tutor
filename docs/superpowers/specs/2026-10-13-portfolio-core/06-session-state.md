# 06 — Session state

[Contracts index](README.md)

## Tables (SQLite via SQLAlchemy 2.0, migrated by Alembic)

| Table | Key columns |
|---|---|
| `users` | id, username (unique, `^[a-z0-9_]{3,32}$`), password_hash (argon2), created_at |
| `study_sessions` | id, user_id, mode (`practice`), topics (JSON), started_at, ended_at |
| `session_items` | id, session_id, item_id, content_version, sequence, state, revision, served_at, completed_at, tries_used |
| `submissions` | id, **submission_id (unique)**, session_item_id, answer_kind, answer_json, answer_latex, created_at |
| `attempt_results` | id, submission_pk (unique), status, reason, method, verifier_version, worker_ms, queue_ms, seconds_on_item, counts_as_try |
| `item_events` | id, session_item_id, kind (`reveal`, `skip`, `advance`), created_at |

- **A `session_items` row is one presentation.** Showing the same problem again later creates a **new** row with fresh tries and timing. Previous exposure stays queryable for mastery and selection.
- **A reveal is an event.** Historical answers are never edited.
- `seconds_on_item` = submit time − `served_at`, computed by the server. Refreshing the page **never** changes `served_at`.

## State machine for a presentation

```
active ──submit: correct──────────────▶ answered (feedback shown)
active ──submit: incorrect, tries<3───▶ active
active ──submit: incorrect, tries=3───▶ exhausted
active ──submit: unable_to_verify─────▶ active   (no try consumed; skip becomes available)
active | exhausted ──reveal───────────▶ revealed  (exhausted only)
active ──skip─────────────────────────▶ completed
answered | exhausted | revealed ──advance──▶ completed (next presentation created)
```

- `revision` increments on every state change.
- Format issues ([02](02-answer-contracts.md)) and `verifier_busy` change nothing.
- Only `incorrect` consumes a try. `unable_to_verify` never does, and the student may skip.

## Submission protocol (atomic and idempotent)

1. **Replay check.** If `submission_id` already exists, return its stored result unchanged (the client retried).
2. **Short transaction A:** load the presentation and check ownership (403), `state == active` and `revision == item_revision`. A mismatch → 409 `stale_item`. Insert the `submissions` row, whose unique constraint stops a concurrent duplicate. Commit.
3. **Grade outside any transaction** via `VerifierPool.submit`.
   - On `VerifierBusy`, delete the reserved submission row and return 503.
4. **Short transaction B:** re-read the presentation.
   - If `revision` changed since step 2 → store the result with `counts_as_try = false` and return 409 `stale_item`.
   - Otherwise insert `attempt_results`, apply the state transition, increment `revision` and commit.
5. **Two different `submission_id`s racing on the same revision:** step 2 lets both reserve, and step 4 lets exactly one win. The loser gets 409. This is tested with genuinely overlapping requests (threads plus a slow `check_fn`).

## Reads and actions

- `GET /api/sessions/{id}/current` is **read-only**. It returns the active presentation's public DTO, its `revision` and the allowed actions.
- Mutations are POST only: `/start`, `/submit`, `/advance`, `/skip`, `/reveal`. Every one carries `item_revision`.
- `reveal` is allowed only in `exhausted`. It returns the expected answer's display LaTeX.

## Selection (core)

- **Textbook order** within the chosen topics: `topic.order`, then `difficulty`, then `id`.
- The next problem is the first one never answered correctly. Prefer unseen problems, then ones whose latest result was incorrect, the oldest first.
- When nothing is left → session `ended_at` is set, and the response is `{done: true, reason}`.
- Revealed, skipped and `unable_to_verify` results are excluded from future mastery calculations. They are kept as exposure.
