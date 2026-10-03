"""Booking-risk API. Confirm calls POST /v1/booking-risk."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.catalog import SCENARIOS, booking_from_payload
from app.db import init_db, make_engine
from app.domain import POLICY_VERSION, apply_model_hold, evaluate
from app.explain import explain
from app.model import ensure_model, hold_threshold, score_features
from app.repository import (
    add_review,
    find_assessment,
    list_accounts,
    list_assessments,
    load_account,
    recent_attempts,
    reset_demo,
    save_assessment,
    to_api,
)

ENGINE = None
SessionLocal = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ENGINE, SessionLocal
    ENGINE = make_engine()
    SessionLocal = init_db(ENGINE)
    ensure_model()
    yield


app = FastAPI(title="Booking Risk", version="0.2.0", lifespan=lifespan)
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


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    action: str = Field(pattern="^(release|uphold|block)$")
    note: str = ""


@app.get("/v1/health")
def health():
    meta = ensure_model()
    return {
        "ok": True,
        "policy_version": POLICY_VERSION,
        "model": meta["algorithm"],
        "hold_threshold": meta["threshold"],
        "steps": [
            "booking",
            "account_snapshot",
            "rules",
            "score",
            "policy",
            "audit",
            "explanation",
            "review",
        ],
    }


@app.get("/v1/accounts")
def accounts():
    with SessionLocal() as session:
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
            for account in list_accounts(session)
        ]


@app.get("/v1/scenarios")
def scenarios():
    return SCENARIOS


@app.get("/v1/decisions")
def decisions(limit: int = 30):
    with SessionLocal() as session:
        return [to_api(row) for row in list_assessments(session, limit)]


@app.post("/v1/booking-risk")
def booking_risk(body: BookingIn):
    payload = body.model_dump()
    booking = booking_from_payload(payload)
    account_number = (booking.billed_account or "").upper() or None
    if account_number:
        booking.billed_account = account_number
    if booking.shipper_account:
        booking.shipper_account = booking.shipper_account.upper()

    with SessionLocal() as session:
        if booking.tx_id:
            existing = find_assessment(session, booking.tx_id)
            if existing is not None:
                return to_api(existing)

        account = load_account(session, account_number)
        recent = recent_attempts(session, account_number) + (1 if account_number else 0)
        ruled = evaluate(booking, account, recent)
        probability = score_features(ruled.features)
        assessment = apply_model_hold(ruled, probability, hold_threshold())
        note, source = explain(assessment, booking, probability)
        tx_id = booking.tx_id or uuid.uuid4().hex[:16]
        row = save_assessment(session, booking, assessment, probability, note, source, tx_id, recent)
        return to_api(row)


@app.post("/v1/decisions/{tx_id}/review")
def review(tx_id: str, body: ReviewIn):
    with SessionLocal() as session:
        row = add_review(session, tx_id, body.reviewer.strip(), body.action, body.note.strip())
        if row is None:
            raise HTTPException(status_code=404, detail="No assessment for that tx")
        return to_api(row)


@app.post("/v1/reset")
def reset():
    with SessionLocal() as session:
        reset_demo(session)
    return {"ok": True}
