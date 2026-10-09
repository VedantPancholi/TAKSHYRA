import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_engine = None


def engine():
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


def session() -> Generator[Session, None, None]:
    with sessionmaker(engine(), expire_on_commit=False)() as db:
        yield db
