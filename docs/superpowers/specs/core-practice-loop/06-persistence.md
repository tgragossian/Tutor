[Index](../2026-10-13-core-practice-loop-design.md) · [Review](../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 256–270. Review findings remain unresolved.

## 5. User data (SQLite via SQLAlchemy 2.0, Alembic migrations)

| Table | Columns |
|---|---|
| `users` | id, username (unique, 3–32 chars `[a-z0-9_]`), password_hash (argon2), created_at |
| `study_sessions` | id, user_id, mode (`diagnostic` \| `practice` \| `recap`), exam_conditions (`closed_book` \| `formula_sheet` \| `open_notes`), topics (JSON list), minutes_budget, warmup_enabled, current_item_id, current_item_served_at, started_at, ended_at |
| `attempts` | id, user_id, study_session_id, item_id, item_kind (`problem` \| `recall` \| `concept`), item_version, answer_latex, answer_mathjson, verdict_status, verdict_reason, verdict_method, attempt_number, is_first_attempt, seconds_spent, hints_used (always 0 in sub-project 1), revealed (bool), created_at |

- `seconds_spent` is computed **server-side** as submit time minus `current_item_served_at`.
- A submission for an item that is not the session's current item is rejected with `409`.
- Mastery is **derived** from `attempts`, never stored.
- The `attempts` table is the future training data for knowledge tracing: user, item, skill, correctness, time.

---

<!-- End preserved source. -->
