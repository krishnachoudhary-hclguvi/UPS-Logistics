"""Relational schema for the account snapshot, the audit log, and reviews."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccountRow(Base):
    __tablename__ = "accounts"

    account_number: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16))
    inbound_policy: Mapped[str] = mapped_column(String(32))
    mostly_domestic_ground: Mapped[bool] = mapped_column(Boolean)
    weekly_pace: Mapped[float] = mapped_column(Float)
    median_weight_kg: Mapped[float] = mapped_column(Float)
    shipment_count_90d: Mapped[int] = mapped_column(Integer)

    postals: Mapped[list[AccountPostalRow]] = relationship(back_populates="account")
    users: Mapped[list[AccountUserRow]] = relationship(back_populates="account")
    parties: Mapped[list[AccountPartyRow]] = relationship(back_populates="account")


class AccountPostalRow(Base):
    __tablename__ = "account_postals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(ForeignKey("accounts.account_number"), index=True)
    postal_code: Mapped[str] = mapped_column(String(16))
    country_code: Mapped[str] = mapped_column(String(2), default="IN")
    account: Mapped[AccountRow] = relationship(back_populates="postals")


class AccountUserRow(Base):
    __tablename__ = "account_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(ForeignKey("accounts.account_number"), index=True)
    ups_user_id: Mapped[str] = mapped_column(String(64))
    account: Mapped[AccountRow] = relationship(back_populates="users")


class AccountPartyRow(Base):
    __tablename__ = "account_parties"
    __table_args__ = (UniqueConstraint("account_number", "shipper_number", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(ForeignKey("accounts.account_number"), index=True)
    shipper_number: Mapped[str] = mapped_column(String(16))
    kind: Mapped[str] = mapped_column(String(16))
    account: Mapped[AccountRow] = relationship(back_populates="parties")


class AttemptRow(Base):
    __tablename__ = "booking_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(16), index=True)
    tx_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AssessmentRow(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tx_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    channel: Mapped[str] = mapped_column(String(32))
    payment_type: Mapped[str] = mapped_column(String(32))
    billed_account: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    shipper_account: Mapped[str | None] = mapped_column(String(16), nullable=True)
    guest: Mapped[bool] = mapped_column(Boolean)
    ups_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ship_from_postal: Mapped[str] = mapped_column(String(16))
    ship_from_country: Mapped[str] = mapped_column(String(2))
    ship_to_postal: Mapped[str] = mapped_column(String(16))
    ship_to_country: Mapped[str] = mapped_column(String(2))
    weight_kg: Mapped[float] = mapped_column(Float)
    service: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    policy_version: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[str] = mapped_column(Text)
    explanation_source: Mapped[str] = mapped_column(String(16))
    features_json: Mapped[str] = mapped_column(Text)
    recent_bookings_1h: Mapped[int] = mapped_column(Integer)

    reasons: Mapped[list[ReasonRow]] = relationship(back_populates="assessment", order_by="ReasonRow.position")
    reviews: Mapped[list[ReviewRow]] = relationship(back_populates="assessment", order_by="ReviewRow.id")


class ReasonRow(Base):
    __tablename__ = "assessment_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(64))
    assessment: Mapped[AssessmentRow] = relationship(back_populates="reasons")


class ReviewRow(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    reviewer: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, default="")
    assessment: Mapped[AssessmentRow] = relationship(back_populates="reviews")
