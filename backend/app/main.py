"""Booking-risk prototype. Confirm calls POST /v1/booking-risk."""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.catalog import ACCOUNTS, RUSH_RECENT_1H, SCENARIOS, account_map, booking_from_payload
from app.db import AccountRow, AttemptRow, DecisionRow, init_db, make_engine, recent_attempts
from app.domain import POLICY_VERSION, apply_model_hold, evaluate
from app.explain import explain
from app.model import ensure_model, hold_threshold, score_features

ENGINE = None
SessionLocal = None


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ENGINE, SessionLocal
    ENGINE = make_engine()
    SessionLocal = init_db(ENGINE)
    ensure_model()
    yield


app = FastAPI(title="Booking Risk", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class BookingIn(BaseModel):
    tx_id: str | None = None
    channel: str = "web_single_page"
    ups_user_id: str | None = None
    guest: bool = False
    payment_type: str = Field(pattern="^(bill_shipper|bill_receiver|bill_third_party|card)$")
    billed_account: str | None = None
    shipper_account: str | None = None
    ship_from_postal: str
    ship_from_country: str = "IN"
    ship_to_postal: str
    ship_to_country: str = "IN"
    weight_kg: float = Field(gt=0, lt=1000)
    service: str = Field(pattern="^(ground|express|international)$")
    package_count: int = 1
    packaging: str = "customer"
    declared_value: float | None = None


def _account_from_row(row: AccountRow | None):
    if row is None:
        return None
    return account_map().get(row.account_number)


@app.get("/v1/health")
def health():
    meta = ensure_model()
    return {
        "ok": True,
        "policy_version": POLICY_VERSION,
        "model": meta["algorithm"],
        "hold_threshold": meta["threshold"],
    }


@app.get("/v1/accounts")
def accounts():
    return [
        {
            "account_number": account.account_number,
            "name": account.name,
            "status": account.status,
            "inbound_policy": account.inbound_policy,
            "weekly_pace": account.weekly_pace,
            "median_weight_kg": account.median_weight_kg,
            "shipment_count_90d": account.shipment_count_90d,
            "ship_from_postals": account.ship_from_postals,
            "linked_user_ids": account.linked_user_ids,
        }
        for account in ACCOUNTS
    ]


@app.get("/v1/scenarios")
def scenarios():
    return SCENARIOS


@app.get("/v1/decisions")
def decisions(limit: int = 30):
    with SessionLocal() as session:
        rows = session.scalars(select(DecisionRow).order_by(DecisionRow.id.desc()).limit(limit)).all()
        return [_decision_out(row) for row in rows]


@app.post("/v1/booking-risk")
def booking_risk(body: BookingIn):
    payload = body.model_dump()
    booking = booking_from_payload(payload)
    account_number = (booking.billed_account or "").upper() or None
    if account_number:
        booking.billed_account = account_number

    with SessionLocal() as session:
        row = session.get(AccountRow, account_number) if account_number else None
        account = _account_from_row(row)
        # This attempt counts toward the hourly pace.
        recent = recent_attempts(session, account_number) + (1 if account_number else 0)
        ruled = evaluate(booking, account, recent)
        probability = score_features(ruled.features)
        assessment = apply_model_hold(ruled, probability, hold_threshold())
        note, source = explain(assessment, booking, probability)
        tx_id = booking.tx_id or uuid.uuid4().hex[:16]
        if account_number:
            session.add(AttemptRow(account_number=account_number, created_at=_utcnow()))
        record = DecisionRow(
            tx_id=tx_id,
            created_at=_utcnow(),
            billed_account=account_number,
            decision=assessment.decision,
            score=f"{probability:.4f}",
            reason_codes=json.dumps(assessment.reason_codes),
            explanation=note,
            explanation_source=source,
            features=json.dumps({"features": assessment.features, "facts": assessment.summary_facts}),
            request_json=json.dumps(payload),
            policy_version=POLICY_VERSION,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return _decision_out(record)


@app.post("/v1/reset")
def reset_demo():
    """Clear the queue and restore the seeded burst on Quiet Books."""
    from datetime import timedelta

    with SessionLocal() as session:
        session.execute(delete(DecisionRow))
        session.execute(delete(AttemptRow))
        now = _utcnow()
        for minutes_ago in range(RUSH_RECENT_1H):
            session.add(
                AttemptRow(
                    account_number="5RUSH3",
                    created_at=now - timedelta(minutes=5 + minutes_ago),
                )
            )
        session.commit()
    return {"ok": True}


def _decision_out(row: DecisionRow) -> dict:
    blob = json.loads(row.features)
    return {
        "tx_id": row.tx_id,
        "created_at": row.created_at.isoformat(timespec="seconds"),
        "billed_account": row.billed_account,
        "decision": row.decision,
        "score": float(row.score),
        "reason_codes": json.loads(row.reason_codes),
        "explanation": row.explanation,
        "explanation_source": row.explanation_source,
        "features": blob.get("features", {}),
        "facts": blob.get("facts", {}),
        "policy_version": row.policy_version,
        "booking": json.loads(row.request_json),
    }
