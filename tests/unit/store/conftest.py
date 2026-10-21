from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from mathtutor.store.db import make_engine, make_sessionmaker, upgrade


@pytest.fixture
def db_url(tmp_path: Path) -> str:
    return f"sqlite:///{(tmp_path / 'test.db').as_posix()}"


@pytest.fixture
def db(db_url: str) -> Iterator[Session]:
    url = db_url
    upgrade(url)
    engine = make_engine(url)
    with make_sessionmaker(engine)() as session:
        yield session
    engine.dispose()
