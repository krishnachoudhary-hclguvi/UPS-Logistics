"""Load the account snapshot and store the audit log."""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session, selectinload

from app.catalog import ACCOUNTS, RUSH_RECENT_1H
from app.clock import utcnow
from app.domain import POLICY_VERSION, AccountSnapshot, Booking
from app.schema import (
    AccountPartyRow,
    AccountPostalRow,
    AccountRow,
    AccountUserRow,
    AssessmentRow,
    AttemptRow,
    Base,
    ReasonRow,
    ReviewRow,
)


def prepare(engine) -> None:
    """Create tables. Drop the old blob schema if this database still has it."""
    names = set(inspect(engine).get_table_names())
    if "accounts" in names:
        columns = {column["name"] for column in inspect(engine).get_columns("accounts")}
        if "payload" in columns or "name" not in columns:
            Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed(session: Session) -> None:
    if session.scalar(select(AccountRow).limit(1)) is not None:
        return
    for account in ACCOUNTS:
        session.add(
            AccountRow(
                account_number=account.account_number,
                name=account.name,
                status=account.status,
                inbound_policy=account.inbound_policy,
                mostly_domestic_ground=account.mostly_domestic_ground,
                weekly_pace=account.weekly_pace,
                median_weight_kg=account.median_weight_kg,
                shipment_count_90d=account.shipment_count_90d,
            )
        )
        for postal in account.ship_from_postals:
            session.add(AccountPostalRow(account_number=account.account_number, postal_code=postal, country_code="IN"))
        for user in account.linked_user_ids:
            session.add(AccountUserRow(account_number=account.account_number, ups_user_id=user))
        for shipper in account.exception_shippers:
            session.add(
                AccountPartyRow(account_number=account.account_number, shipper_number=shipper.upper(), kind="exception")
            )
        for shipper in account.known_third_parties:
            session.add(
                AccountPartyRow(account_number=account.account_number, shipper_number=shipper.upper(), kind="known_payer")
            )
    _seed_rush(session)
    session.commit()


def list_accounts(session: Session) -> list[AccountSnapshot]:
    rows = session.scalars(
        select(AccountRow).options(
            selectinload(AccountRow.postals),
            selectinload(AccountRow.users),
            selectinload(AccountRow.parties),
        )
    ).all()
    return [load_account(session, row.account_number) for row in rows]


def load_account(session: Session, account_number: str | None) -> AccountSnapshot | None:
    if not account_number:
        return None
    row = session.scalar(
        select(AccountRow)
        .where(AccountRow.account_number == account_number)
        .options(
            selectinload(AccountRow.postals),
            selectinload(AccountRow.users),
            selectinload(AccountRow.parties),
        )
    )
    if row is None:
        return None
    return AccountSnapshot(
        account_number=row.account_number,
        name=row.name,
        status=row.status,
        inbound_policy=row.inbound_policy,
        exception_shippers=[party.shipper_number for party in row.parties if party.kind == "exception"],
        known_third_parties=[party.shipper_number for party in row.parties if party.kind == "known_payer"],
        linked_user_ids=[user.ups_user_id for user in row.users],
        ship_from_postals=[postal.postal_code for postal in row.postals],
        mostly_domestic_ground=row.mostly_domestic_ground,
        weekly_pace=row.weekly_pace,
        median_weight_kg=row.median_weight_kg,
        shipment_count_90d=row.shipment_count_90d,
    )


def recent_attempts(session: Session, account_number: str | None) -> int:
    if not account_number:
        return 0
    cutoff = utcnow() - timedelta(hours=1)
    rows = session.scalars(
        select(AttemptRow).where(
            AttemptRow.account_number == account_number,
            AttemptRow.created_at >= cutoff,
        )
    ).all()
    return len(rows)


def find_assessment(session: Session, tx_id: str) -> AssessmentRow | None:
    return session.scalar(
        select(AssessmentRow)
        .where(AssessmentRow.tx_id == tx_id)
        .options(selectinload(AssessmentRow.reasons), selectinload(AssessmentRow.reviews))
    )


def save_assessment(session: Session, booking: Booking, assessment, score: float, note: str, source: str, tx_id: str, recent: int) -> AssessmentRow:
    row = AssessmentRow(
        tx_id=tx_id,
        created_at=utcnow(),
        channel=booking.channel,
        payment_type=booking.payment_type,
        billed_account=booking.billed_account,
        shipper_account=(booking.shipper_account or None),
        guest=booking.guest,
        ups_user_id=booking.ups_user_id,
        ship_from_postal=booking.ship_from_postal,
        ship_from_country=booking.ship_from_country,
        ship_to_postal=booking.ship_to_postal,
        ship_to_country=booking.ship_to_country,
        weight_kg=booking.weight_kg,
        service=booking.service,
        decision=assessment.decision,
        score=score,
        policy_version=POLICY_VERSION,
        explanation=note,
        explanation_source=source,
        features_json=json.dumps({"features": assessment.features, "facts": assessment.summary_facts}),
        recent_bookings_1h=recent,
    )
    session.add(row)
    session.flush()
    for position, code in enumerate(assessment.reason_codes):
        session.add(ReasonRow(assessment_id=row.id, position=position, code=code))
    if booking.billed_account:
        session.add(AttemptRow(account_number=booking.billed_account, tx_id=tx_id, created_at=utcnow()))
    session.commit()
    return find_assessment(session, tx_id)


def list_assessments(session: Session, limit: int) -> list[AssessmentRow]:
    return list(
        session.scalars(
            select(AssessmentRow)
            .options(selectinload(AssessmentRow.reasons), selectinload(AssessmentRow.reviews))
            .order_by(AssessmentRow.id.desc())
            .limit(limit)
        ).all()
    )


def add_review(session: Session, tx_id: str, reviewer: str, action: str, note: str) -> AssessmentRow | None:
    row = find_assessment(session, tx_id)
    if row is None:
        return None
    session.add(
        ReviewRow(
            assessment_id=row.id,
            created_at=utcnow(),
            reviewer=reviewer,
            action=action,
            note=note,
        )
    )
    session.commit()
    session.expire_all()
    return find_assessment(session, tx_id)


def reset_demo(session: Session) -> None:
    session.execute(delete(ReviewRow))
    session.execute(delete(ReasonRow))
    session.execute(delete(AssessmentRow))
    session.execute(delete(AttemptRow))
    _seed_rush(session)
    session.commit()


def _seed_rush(session: Session) -> None:
    now = utcnow()
    for minutes_ago in range(RUSH_RECENT_1H):
        session.add(
            AttemptRow(
                account_number="5RUSH3",
                tx_id=None,
                created_at=now - timedelta(minutes=5 + minutes_ago),
            )
        )


def to_api(row: AssessmentRow) -> dict:
    blob = json.loads(row.features_json)
    reviews = [
        {
            "reviewer": review.reviewer,
            "action": review.action,
            "note": review.note,
            "created_at": review.created_at.isoformat(timespec="seconds"),
        }
        for review in row.reviews
    ]
    return {
        "tx_id": row.tx_id,
        "created_at": row.created_at.isoformat(timespec="seconds"),
        "billed_account": row.billed_account,
        "decision": row.decision,
        "score": float(row.score),
        "reason_codes": [reason.code for reason in row.reasons],
        "explanation": row.explanation,
        "explanation_source": row.explanation_source,
        "features": blob.get("features", {}),
        "facts": blob.get("facts", {}),
        "policy_version": row.policy_version,
        "reviews": reviews,
        "booking": {
            "channel": row.channel,
            "payment_type": row.payment_type,
            "billed_account": row.billed_account,
            "shipper_account": row.shipper_account,
            "guest": row.guest,
            "ups_user_id": row.ups_user_id,
            "ship_from_postal": row.ship_from_postal,
            "ship_from_country": row.ship_from_country,
            "ship_to_postal": row.ship_to_postal,
            "ship_to_country": row.ship_to_country,
            "weight_kg": row.weight_kg,
            "service": row.service,
        },
    }
