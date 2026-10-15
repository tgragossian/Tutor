# Task 12: Practice service and submit protocol

[Milestone B plan](../README.md) · [Spec 06](../../../../specs/2026-10-13-portfolio-core/06-session-state.md) · Ruling R5

**Files:**
- Create: `src/mathtutor/application/selection.py`, `practice.py`
- Create: `tests/unit/application/test_selection.py`, `test_practice.py`, `tests/integration/test_submit_races.py`

**Interfaces:**
- Consumes: `LoadedContent`, `servable` (content); `VerifierPool`, `CheckRequest`, `SubmittedAnswer`, `VerifierBusy` (verify); models and `make_sessionmaker` (store); errors (task 11).
- Produces:
  - `def next_item_id(content: LoadedContent, topics: list[str], history: list[tuple[str, VerdictStatus | None, datetime]]) -> str | None` — spec 06 selection: textbook order; first never answered correctly; unseen first, then latest-incorrect oldest first.
  - `@dataclass(frozen=True) class ItemView` — `session_item_id, revision, state, item_id, statement_html, answer_kind, precision_hint, choices: list[tuple[str, str]] | None, source: Source, allowed_actions: list[Action], tries_left: int, last_outcome: Verdict | FormatIssue | None, revealed_latex: str | None`
  - `@dataclass(frozen=True) class SubmitView` — `outcome: Verdict | FormatIssue, item: ItemView, replayed: bool`
  - `class PracticeService(sessions, content, pool, clock)` with methods (every one takes `user_id`; another user's session → `Forbidden`; unknown → `NotFound`):
    - `start_session(user_id, topics: list[str]) -> int` — creates the session **and its first presentation** (unknown topic → `InvalidAction`)
    - `current_item(user_id, session_id) -> ItemView | Done` (`Done(reason: str)`); **read-only**: never inserts or updates a row
    - `submit_answer(user_id, session_id, submission_id: UUID, session_item_id: int, item_revision: int, answer: SubmittedAnswer) -> SubmitView`
    - `advance / skip / reveal(user_id, session_id, item_revision) -> ItemView | Done` — each inserts an `item_events` row; advance and skip create the next presentation; `reveal` sets `revealed_latex`
    - `session_summary(user_id) -> list[SessionSummary]` (`session_id, topics, started_at, answered, correct`)
  - `precision_hint`: `"Round to N decimal places"` or `"Give an exact answer"`; `None` for other kinds.

**Protocol:** implement spec 06 "Submission protocol" steps 1–5 verbatim, with two additions:
- Format issues (`check` returns `FormatIssue`) delete the reservation and return the issue; nothing changes (spec 02).
- R5: on replay, a reservation with no `attempt_results` and `created_at` older than 10 s is graded again (steps 3–4) instead of returning empty.

- [ ] **Step 1: Write the failing tests** (pool replaced by a fake `submit` returning scripted results; races use the real pool with `tests/support/checks.slow`).

```python
def test_selection_textbook_order_and_retry_policy(): ...   # unseen first; then latest-incorrect, oldest first; correct items never return
def test_three_incorrect_exhausts(): ...                    # state active→active→exhausted, tries_left 2,1,0
def test_unable_to_verify_keeps_try_and_allows_skip(): ...
def test_correct_then_advance_creates_new_presentation(): ...
def test_reveal_only_when_exhausted(): ...                  # reveal in active → InvalidAction; in exhausted → revealed_latex set
def test_revisit_gets_fresh_presentation(): ...             # same item later → new session_items row, tries reset
def test_duplicate_submission_id_returns_stored_result(): ...  # second call replayed=True, one attempt_results row
def test_stale_revision_is_409(): ...
def test_other_users_session_forbidden(): ...               # current, submit, advance, skip, reveal all → Forbidden
def test_busy_releases_reservation(): ...                   # VerifierBusy → Busy raised, no submissions row left
def test_format_issue_changes_nothing(): ...
def test_current_is_read_only(): ...                        # two current_item calls: same revision, same served_at
def test_seconds_on_item_from_served_at(): ...              # clock-driven
def test_replay_regrades_orphaned_reservation(): ...        # R5
def test_racing_different_submission_ids_one_wins(): ...    # two threads, same revision, slow check → one 200, one StaleItem
def test_sixteen_concurrent_submits(): ...                  # 16 threads, real SQLite file: only success/StaleItem/Busy, no OperationalError
def test_done_when_all_answered(): ...                      # Done("all_correct"), study_sessions.ended_at set
```

- [ ] **Step 2:** Run `uv run pytest tests/unit/application tests/integration/test_submit_races.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `selection.py`, then `PracticeService`. Every transaction is a `with self.sessions.begin() as db:` block; the pool is called with no transaction open. `revision` increments on every state change; `served_at` is set once, at row creation.
- [ ] **Step 4:** Run `uv run pytest -q && uv run mypy src`. Expected: PASS; run the race file three times to catch flakes.
- [ ] **Step 5: Commit** `feat: practice service with atomic idempotent submissions`.
