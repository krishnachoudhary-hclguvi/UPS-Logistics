from app.catalog import RUSH_RECENT_1H, SCENARIOS, account_map, booking_from_payload
from app.domain import evaluate

EXPECT = {
    "normal": "allow",
    "guest": "step-up",
    "deny": "block",
    "partner": "allow",
    "new_payer": "hold",
    "lane": "hold",
    "velocity": "hold",
    "closed": "block",
    "thin": "step-up",
    "heavy": "allow",
    "card": "allow",
}

CODES = {
    "guest": "UNLINKED_ACCOUNT_ON_GUEST",
    "deny": "INBOUND_POLICY_DENY",
    "new_payer": "NEW_PAYER_RELATIONSHIP",
    "lane": "ORIGIN_LANE_SHIFT",
    "velocity": "VELOCITY_SPIKE",
    "closed": "ACCOUNT_CLOSED",
    "thin": "THIN_HISTORY",
    "card": "CARD_PAYMENT_OUT_OF_SCOPE",
}


def _recent(scenario_id: str) -> int:
    if scenario_id == "velocity":
        return RUSH_RECENT_1H + 1
    return 1


def test_each_demo_scenario_matches_the_rule():
    accounts = account_map()
    assert set(EXPECT) == {item["id"] for item in SCENARIOS}
    for item in SCENARIOS:
        booking = booking_from_payload(item["booking"])
        account = accounts.get(booking.billed_account or "")
        result = evaluate(booking, account, _recent(item["id"]))
        assert result.decision == EXPECT[item["id"]], item["id"]
        if item["id"] in CODES:
            assert CODES[item["id"]] in result.reason_codes


def test_known_partner_is_not_a_new_payer():
    item = next(row for row in SCENARIOS if row["id"] == "partner")
    booking = booking_from_payload(item["booking"])
    result = evaluate(booking, account_map()["2LX8QP"], 1)
    assert result.reason_codes == []
    assert result.decision == "allow"


def test_high_score_holds_and_never_blocks():
    from app.domain import apply_model_hold

    item = next(row for row in SCENARIOS if row["id"] == "normal")
    booking = booking_from_payload(item["booking"])
    result = evaluate(booking, account_map()["9A4K2M"], 1)
    held = apply_model_hold(result, 0.99, 0.5)
    assert held.decision == "hold"
    assert held.reason_codes == ["MODEL_ELEVATED_SCORE"]

    denied = next(row for row in SCENARIOS if row["id"] == "deny")
    booking = booking_from_payload(denied["booking"])
    blocked = evaluate(booking, account_map()["9A4K2M"], 1)
    still = apply_model_hold(blocked, 0.1, 0.5)
    assert still.decision == "block"


def test_thin_history_is_not_upgraded_by_the_model():
    from app.domain import apply_model_hold

    item = next(row for row in SCENARIOS if row["id"] == "thin")
    booking = booking_from_payload(item["booking"])
    result = evaluate(booking, account_map()["4NEW8K"], 1)
    same = apply_model_hold(result, 0.99, 0.2)
    assert same.decision == "step-up"
    assert "MODEL_ELEVATED_SCORE" not in same.reason_codes
