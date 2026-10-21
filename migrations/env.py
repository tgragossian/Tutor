"""Alembic environment: online migrations only, using the app's engine settings (WAL etc.)."""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context

from mathtutor.settings import Settings
from mathtutor.store.db import make_engine
from mathtutor.store.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _url() -> str:
    x_args = context.get_x_argument(as_dictionary=True)
    return (
        x_args.get("url")
        or config.get_main_option("sqlalchemy.url")
        or os.environ.get("MATHTUTOR_DATABASE_URL")
        or Settings().database_url
    )


def run_migrations_online() -> None:
    engine = make_engine(_url())
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=Base.metadata,
                render_as_batch=True,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise SystemExit("offline (--sql) migrations are not supported")
run_migrations_online()
