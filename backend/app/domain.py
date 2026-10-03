"""Account snapshot, booking, rules, and the shared feature vector."""

from __future__ import annotations

from dataclasses import dataclass, field


POLICY_VERSION = "rules-v1+xgb"

FEATURE_NAMES = [
    "account_closed",
    "inbound_deny_hit",
    "guest_unlinked",
    "thin_history",
    "new_payer",
    "origin_unseen",
    "express_or_international",
    "domestic_ground_history",
    "velocity_ratio",
    "weight_ratio",
    "card_payment",
]


@dataclass
class AccountSnapshot:
    account_number: str
    name: str
    status: str
    inbound_policy: str
    exception_shippers: list[str] = field(default_factory=list)
    known_third_parties: list[str] = field(default_factory=list)
    linked_user_ids: list[str] = field(default_factory=list)
    ship_from_postals: list[str] = field(default_factory=list)
    destination_countries: list[str] = field(default_factory=list)
    usual_services: list[str] = field(default_factory=list)
    mostly_domestic_ground: bool = True
    weekly_pace: float = 1
    median_weight_kg: float = 5
    shipment_count_90d: int = 0


@dataclass
class Booking:
    payment_type: str
    ship_from_postal: str
    ship_from_country: str
    ship_to_postal: str
    ship_to_country: str
    weight_kg: float
    service: str
    guest: bool = False
    ups_user_id: str | None = None
    billed_account: str | None = None
    shipper_account: str | None = None
    channel: str = "web_single_page"
    package_count: int = 1
    packaging: str = "customer"
    declared_value: float | None = None
    tx_id: str | None = None


@dataclass
class Assessment:
    decision: str
    reason_codes: list[str]
    features: dict
    summary_facts: dict


def _velocity_limit(weekly_pace: float) -> int:
    daily = max(weekly_pace, 0) / 7
    return max(6, round(3 * daily))


def build_features(booking: Booking, account: AccountSnapshot | None, recent_1h: int) -> dict:
    if account is None:
        return {name: 0 for name in FEATURE_NAMES} | {
            "velocity_ratio": 0,
            "weight_ratio": 1,
            "card_payment": 1 if booking.payment_type == "card" else 0,
        }

    account_billed = booking.payment_type in {"bill_shipper", "bill_receiver", "bill_third_party"}
    third_party = booking.payment_type in {"bill_receiver", "bill_third_party"}
    shipper = (booking.shipper_account or "").upper()
    origin_unseen = booking.ship_from_postal not in account.ship_from_postals
    express_or_international = booking.service in {"express", "international"} or booking.ship_to_country != booking.ship_from_country
    inbound_deny_hit = (
        account.inbound_policy == "deny_third_party"
        and third_party
        and shipper not in {s.upper() for s in account.exception_shippers}
    )
    linked = {u.lower() for u in account.linked_user_ids}
    user = (booking.ups_user_id or "").lower()
    guest_unlinked = account_billed and (booking.guest or not user or user not in linked)
    new_payer = (
        third_party
        and shipper not in {s.upper() for s in account.known_third_parties}
        and origin_unseen
    )
    thin_history = account.shipment_count_90d < 8 and account.status == "open"
    daily = max(account.weekly_pace / 7, 0.25)
    velocity_ratio = recent_1h / daily
    weight_ratio = booking.weight_kg / account.median_weight_kg if account.median_weight_kg else 1
    return {
        "account_closed": 1 if account.status == "closed" else 0,
        "inbound_deny_hit": 1 if inbound_deny_hit else 0,
        "guest_unlinked": 1 if guest_unlinked else 0,
        "thin_history": 1 if thin_history else 0,
        "new_payer": 1 if new_payer else 0,
        "origin_unseen": 1 if origin_unseen else 0,
        "express_or_international": 1 if express_or_international else 0,
        "domestic_ground_history": 1 if account.mostly_domestic_ground else 0,
        "velocity_ratio": round(velocity_ratio, 3),
        "weight_ratio": round(weight_ratio, 3),
        "card_payment": 1 if booking.payment_type == "card" else 0,
    }


def evaluate(booking: Booking, account: AccountSnapshot | None, recent_1h: int) -> Assessment:
    """Rules decide. Severity is block, then hold, then step-up, then allow."""
    features = build_features(booking, account, recent_1h)
    codes: list[str] = []

    if booking.payment_type == "card":
        return Assessment(
            decision="allow",
            reason_codes=["CARD_PAYMENT_OUT_OF_SCOPE"],
            features=features,
            summary_facts={"recent_bookings_1h": recent_1h},
        )

    if account is None:
        return Assessment(
            decision="step-up",
            reason_codes=["ACCOUNT_UNKNOWN"],
            features=features,
            summary_facts={"recent_bookings_1h": recent_1h},
        )

    limit = _velocity_limit(account.weekly_pace)
    facts = {
        "recent_bookings_1h": recent_1h,
        "velocity_limit_1h": limit,
        "weekly_pace": account.weekly_pace,
        "median_weight_kg": account.median_weight_kg,
        "shipment_count_90d": account.shipment_count_90d,
        "origin_seen": features["origin_unseen"] == 0,
        "account_name": account.name,
    }

    if account.status == "closed":
        codes.append("ACCOUNT_CLOSED")
    if features["inbound_deny_hit"]:
        codes.append("INBOUND_POLICY_DENY")
    if features["new_payer"]:
        codes.append("NEW_PAYER_RELATIONSHIP")
    if (
        features["origin_unseen"]
        and features["express_or_international"]
        and features["domestic_ground_history"]
    ):
        codes.append("ORIGIN_LANE_SHIFT")
    if recent_1h >= limit:
        codes.append("VELOCITY_SPIKE")
    if features["guest_unlinked"]:
        codes.append("UNLINKED_ACCOUNT_ON_GUEST")
    if features["thin_history"]:
        codes.append("THIN_HISTORY")

    if "ACCOUNT_CLOSED" in codes or "INBOUND_POLICY_DENY" in codes:
        decision = "block"
    elif any(code in codes for code in ("NEW_PAYER_RELATIONSHIP", "ORIGIN_LANE_SHIFT", "VELOCITY_SPIKE")):
        decision = "hold"
    elif "UNLINKED_ACCOUNT_ON_GUEST" in codes or "THIN_HISTORY" in codes:
        decision = "step-up"
    else:
        decision = "allow"
        codes = []

    return Assessment(decision=decision, reason_codes=codes, features=features, summary_facts=facts)


def apply_model_hold(assessment: Assessment, score: float, threshold: float) -> Assessment:
    """A high score can hold an otherwise clean booking. It never blocks, and it stays quiet on thin history and cards."""
    if assessment.features.get("card_payment"):
        return assessment
    if assessment.features.get("thin_history"):
        return assessment
    if assessment.decision != "allow":
        return assessment
    if score < threshold:
        return assessment
    codes = assessment.reason_codes + ["MODEL_ELEVATED_SCORE"]
    return Assessment(
        decision="hold",
        reason_codes=codes,
        features=assessment.features,
        summary_facts=assessment.summary_facts,
    )
