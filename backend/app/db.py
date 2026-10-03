"""SQLite for the prototype. Point DATABASE_URL at Postgres to use that instead."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.catalog import ACCOUNTS, RUSH_RECENT_1H

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_URL = f"sqlite:///{DATA_DIR / 'prototype.db'}"


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = "accounts"

    account_number: Mapped[str] = mapped_column(String(16), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class AttemptRow(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class DecisionRow(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tx_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    billed_account: Mapped[str | None] = mapped_column(String(16), nullable=True)
    decision: Mapped[str] = mapped_column(String(16))
    score: Mapped[str] = mapped_column(String(16))
    reason_codes: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    explanation_source: Mapped[str] = mapped_column(String(16))
    features: Mapped[str] = mapped_column(Text)
    request_json: Mapped[str] = mapped_column(Text)
    policy_version: Mapped[str] = mapped_column(String(32))


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def make_engine(url: str | None = None):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url or os.environ.get("DATABASE_URL", DEFAULT_URL), future=True)
    return engine


def init_db(engine) -> None:
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        existing = session.scalar(select(AccountRow).limit(1))
        if existing is None:
            for account in ACCOUNTS:
                session.add(
                    AccountRow(
                        account_number=account.account_number,
                        payload=json.dumps(account.__dict__),
                    )
                )
            now = _utcnow()
            rush = next(account for account in ACCOUNTS if account.account_number == "5RUSH3")
            for minutes_ago in range(RUSH_RECENT_1H):
                session.add(
                    AttemptRow(
                        account_number=rush.account_number,
                        created_at=now - timedelta(minutes=5 + minutes_ago),
                    )
                )
            session.commit()
    return Session


def recent_attempts(session, account_number: str | None) -> int:
    if not account_number:
        return 0
    cutoff = _utcnow() - timedelta(hours=1)
    rows = session.scalars(
        select(AttemptRow).where(
            AttemptRow.account_number == account_number,
            AttemptRow.created_at >= cutoff,
        )
    ).all()
    return len(rows)
