[Index](../../2026-10-13-core-practice-loop.md) · [Review](../../../../reviews/2026-10-13/README.md)

> Preserved 2026-10-13 draft; original lines 608–644. Review findings remain unresolved.

### Task 12: Persistence (SQLAlchemy + Alembic)

**Files:**
- Create: `src/mathtutor/store/__init__.py`, `models.py`, `db.py`, `repo.py`, `alembic.ini`, `migrations/env.py`, `migrations/versions/0001_initial.py`, `tests/store/test_repo.py`, `tests/store/test_migrations.py`

**Interfaces:**
- Produces:
  - ORM classes `User`, `StudySession`, `Attempt` with exactly the §5 columns. `topics` is a JSON column; times are timezone-aware UTC.
  - `make_engine(url: str) -> Engine` (SQLite: `PRAGMA foreign_keys=ON`, WAL)
  - `make_sessionmaker(engine) -> sessionmaker[Session]`
  - in `repo.py`, all taking `db: Session`:
    - `create_user(db, username, password_hash) -> User`, raising `UsernameTaken`
    - `get_user_by_username(db, username) -> User | None`
    - `create_study_session(db, user_id: int, plan: SessionPlan, now: datetime) -> StudySession`
    - `get_study_session(db, session_id) -> StudySession | None`
    - `set_current_item(db, s: StudySession, item_id: str | None, now: datetime) -> None`
    - `record_attempt(db, **fields) -> Attempt`
    - `attempts_for_user(db, user_id) -> list[Attempt]` (by created_at)
    - `attempts_for_session(db, session_id) -> list[Attempt]`
    - `end_session(db, s, now) -> None`
    - `set_warmup(db, s, enabled: bool) -> None`
  - Consumes `SessionPlan` from `mathtutor.domain` (Task 11).

- [ ] **Step 1: Write the failing tests:**
  - create/get user
  - a duplicate username raises `UsernameTaken`
  - session round-trips the topics list
  - attempts are ordered
  - foreign keys are enforced
  - `test_migrations`: `alembic upgrade head` on an empty temp DB produces the same tables and columns as `Base.metadata`
- [ ] **Step 2:** Run `uv run pytest tests/store -v`. Expected: FAIL.
- [ ] **Step 3:** Implement. Generate `0001_initial` with autogenerate, then hand-check it.
- [ ] **Step 4:** Rerun the tests. Expected: PASS.
- [ ] **Step 5: Commit** `feat(store): models, repository, initial migration`.

---

<!-- End preserved source. -->
