"""Database connection. The tables live in app.schema."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.clock import utcnow
from app.repository import prepare, seed

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_URL = f"sqlite:///{DATA_DIR / 'prototype.db'}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_engine(url: str | None = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_URL), future=True)


def init_db(engine):
    prepare(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        seed(session)
    return Session
