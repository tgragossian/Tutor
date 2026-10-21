"""Engine and session factories, plus programmatic Alembic upgrades."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATIONS = REPO_ROOT / "migrations"
BUSY_TIMEOUT_MS = 5000


def _set_sqlite_pragmas(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def make_engine(url: str) -> Engine:
    """Build an engine. SQLite gets WAL, a 5 s busy timeout and enforced foreign keys."""
    if make_url(url).get_backend_name() != "sqlite":
        return create_engine(url)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 5})
    event.listen(engine, "connect", _set_sqlite_pragmas)
    return engine


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


def _alembic_config(url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


def _ensure_sqlite_dir(url: str) -> None:
    parsed = make_url(url)
    if parsed.get_backend_name() == "sqlite" and parsed.database not in (None, "", ":memory:"):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)


def upgrade(url: str, revision: str = "head") -> None:
    """Run ``alembic upgrade`` against ``url`` (tests and the release step).

    Creates the SQLite file's directory; app startup itself never writes to disk.
    """
    _ensure_sqlite_dir(url)
    command.upgrade(_alembic_config(url), revision)


def downgrade(url: str, revision: str) -> None:
    command.downgrade(_alembic_config(url), revision)
