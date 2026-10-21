# Task 10: Store — models, migrations, WAL

[Milestone B plan](../README.md) · [Spec 06](../../../../specs/2026-10-13-portfolio-core/06-session-state.md) · Ruling R2

**Status (2026-10-21):** complete in d865179; amended in tasks 11–12 (A2–A5).
Completed recipe below; [app rulings A1–A18](../06-app-track-rulings.md) record amendments.
Validation is recorded in [evidence](../07-verification-evidence.md); commands below are the execution recipe.

**Files:**
- Create: `src/mathtutor/store/__init__.py`, `db.py`, `models.py`
- Create: `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/0001_initial.py`
- Create: `tests/unit/store/test_models.py`, `tests/unit/store/test_migrations.py`
- Modify: `pyproject.toml` (`uv add sqlalchemy alembic`), `src/mathtutor/settings.py`

**Interfaces:**
- Consumes: `ItemState`, `AnswerKind`, `VerdictStatus`, `VerdictReason`, `Method` (domain).
- Produces:
  - `Settings.database_url: str = "sqlite:///data/mathtutor.db"` (env `MATHTUTOR_DATABASE_URL`).
  - `def make_engine(url: str) -> Engine` — for SQLite: `connect_args={"check_same_thread": False, "timeout": 5}`, and on every connect `PRAGMA journal_mode=WAL`, `PRAGMA busy_timeout=5000`, `PRAGMA foreign_keys=ON`.
  - `def make_sessionmaker(engine: Engine) -> sessionmaker[Session]` (`expire_on_commit=False`).
  - `def upgrade(url: str) -> None` — runs `alembic upgrade head` programmatically (used by tests and the release step).
  - ORM classes (SQLAlchemy 2.0 `Mapped[...]` style), tables and columns exactly as spec 06, plus:
    - `web_sessions`: `id` (int pk), `token_hash` (unique, 64 hex), `user_id` (fk), `csrf_token` (str), `created_at`, `expires_at`
    - `session_items` unique `(session_id, sequence)`; `submissions.submission_id` unique (uuid text); `attempt_results.submission_pk` unique
    - indexes: `session_items(session_id, state)`, `submissions(session_item_id)`, `study_sessions(user_id)`
  - Enum columns store string values without CHECK constraints (A2); `attempt_results.applied` records race outcomes (A4).
  - Timestamps are timezone-aware UTC (`UTCDateTime`, A2); the application passes `now` explicitly.

- [x] **Step 1: Write the failing tests.**

```python
def test_upgrade_creates_all_tables(tmp_path): upgrade(url(tmp_path)); assert set(inspect(make_engine(url(tmp_path))).get_table_names()) >= {
    "users", "web_sessions", "study_sessions", "session_items", "submissions", "attempt_results", "item_events", "alembic_version"}
def test_migration_matches_models(tmp_path): ...   # alembic autogenerate diff against Base.metadata is empty
def test_pragmas(tmp_path): ...                    # journal_mode == "wal", busy_timeout == 5000, foreign_keys == 1 on a fresh connection
def test_submission_id_unique(db): ...             # second insert with same submission_id raises IntegrityError
def test_username_unique(db): ...
def test_attempt_result_one_per_submission(db): ...
def test_foreign_keys_enforced(db): ...            # session_item with unknown session_id raises IntegrityError
def test_downgrade_then_upgrade(tmp_path): ...     # alembic downgrade base; upgrade head → same tables
```

- [x] **Step 2:** Run `uv run pytest tests/unit/store -q`. Expected: FAIL (module missing).
- [x] **Step 3: Implement** `db.py`, `models.py` (one declarative `Base`), then `alembic init`-style files by hand; `env.py` reads the URL from `MATHTUTOR_DATABASE_URL` or the `-x url=` argument and uses `Base.metadata`. Write `0001_initial.py` by autogenerate, then review it by hand (SQLite: `render_as_batch=True`).
- [x] **Step 4:** Run `uv run pytest tests/unit/store -q && uv run mypy src`. Expected: PASS. Add `mathtutor.store` to mypy strict.
- [x] **Step 5:** `.gitignore`: add `data/`. `docs/ops/runbook.md` gets one line: migrations run with `alembic upgrade head` before the app starts (wired in task 16).
- [x] **Step 6: Commit** `feat: SQLAlchemy models, Alembic baseline and SQLite WAL settings`.
