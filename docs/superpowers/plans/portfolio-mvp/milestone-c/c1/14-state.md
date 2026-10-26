# C1 tasks 7–8: help state and the spend ledger

[C1 plan](README.md) · [State/accounting spec](../../../../specs/2026-10-26-milestone-c/06-state-and-accounting.md) · Next: [context, generator](15-context-generator.md)

### Task 7: Migration 0004 and ORM models

**Files:** Create `migrations/versions/0004_help.py`; Modify `src/mathtutor/store/models.py`;
Test `tests/unit/store/test_migrations.py` (extend), `tests/unit/store/test_help_models.py`.

**Interfaces:** Produces (all timestamps `UTCDateTime`):
- `User.privacy_epoch: int` (server default 0).
- `ItemHelpState(session_item_id PK FK, hint_level: int = 1, help_seq: int = 0, in_flight: str | None)`.
- `HelpRequestRow(id, request_id: str(36) unique, user_id FK, session_item_id FK, item_revision,
  help_type, confusion_id: str | None, payload_hash: str(64), privacy_epoch, help_seq,
  hint_level: int | None, status: str(16), reason: str(32) | None, model: str | None,
  prompt_version, corpus_hash, index_fingerprint, retrieved_ids: JSON, cited_ids: JSON,
  guard_counts: JSON, calls: int, latency_ms: int | None, arm: str = "none",
  serving_model: str | None, output_json: Text | None, created_at, finished_at: | None,
  cleared_at: | None, next_submission_id: str(36) | None)`. Only `output_json` holds model text.
- `UsageEntry(id, request_id: str(36), user_id: int (no FK), kind: "help" | "eval", call_no,
  model, month: str(7), state: "reserved" | "settled" | "uncertain", reserved_micros,
  settled_micros: int | None, input_tokens, output_tokens, created_at, settled_at)`;
  indexes `(user_id, created_at)` and `(month, state)`. Never deleted by any user action.
- [ ] **Step 1: Failing tests:** `test_upgrade_0003_to_0004_keeps_rows` (populated 0003 DB
  upgrades; existing users get epoch 0), `test_downgrade_0004`, `test_usage_has_no_user_fk`
  (deleting help rows leaves usage), `test_request_id_unique`.
- [ ] **Step 2:** `uv run pytest tests/unit/store -q` → FAIL.
- [ ] **Step 3:** Implement the migration (new tables + one `batch_alter_table` add-column) and models.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(store): help requests, item help state and usage ledger (0004)`.

### Task 8: Ledger — admission, reservations, settlement

**Files:** Create `src/mathtutor/help/ledger.py`; Modify `src/mathtutor/application/errors.py`
(add `HelpLimited`, HTTP 429, code `help_limited`); Test `tests/unit/help/test_ledger.py`.

**Interfaces:** Consumes Task 7 models, `write_transaction`, `HelpConfig`. Produces `Ledger`,
`HelpLimited` (03). `admit` runs inside the caller's `BEGIN IMMEDIATE` transaction: counts the
user's `call_no == 1` entries in the last hour/day, sums the month (`settled_micros` for settled,
`reserved_micros` otherwise), raises `HelpLimited(reason)` with `reason ∈ {"hour", "day",
"budget"}`, else inserts call 1 as `reserved` at worst case. `reserve_call` does the same budget
check in its own short transaction (no rate count). `settle` computes actual micros from tokens
and the tariff, rounding up. A sweeper `reconcile_stale(now)` marks `reserved` older than 120 s
as `uncertain`; `admit` calls it first. Nothing automatically settles `uncertain`; the owner runs
`python -m mathtutor.help.ledger settle-uncertain --month YYYY-MM` after checking the console
(settles at the reserved worst case unless `--micros` is given).

- [ ] **Step 1: Failing tests** (fake clock, real SQLite file):
  - `test_hourly_and_daily_limits`: 30th admission in an hour passes, 31st raises `hour`;
    150/day likewise; limits survive deleting the user's `HelpRequestRow`s.
  - `test_budget_includes_reservations`: with 14,999,000 µ$ settled, a 1,300 µ$ admission fails `budget`.
  - `test_concurrent_admissions_do_not_overspend`: 20 threads admit against a budget for 10;
    exactly 10 succeed.
  - `test_settle_rounds_up`: 1,234 input + 567 output Haiku tokens → 407 µ$ (ceil).
  - `test_uncertain_counts_until_reconciled`: an unsettled reservation becomes `uncertain`
    after 120 s and still counts at its reserved amount in `month_total`.
  - `test_month_rollover_utc`: a reservation made 23:59:59 UTC on the last day belongs to that
    month; the new month starts from settled 0 but an old `uncertain` stays in its own month.
  - `test_clear_history_does_not_reset`: Task 12's clear-history path leaves `month_total` and
    rate counts unchanged (stub the call here; the API test repeats it end to end).
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. No lock is held during provider calls (callers commit before calling).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(help): durable admission and spend ledger`.
