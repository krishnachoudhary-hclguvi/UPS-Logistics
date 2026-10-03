"""Plain-language note. The note cites reason codes. It does not choose the action."""

from __future__ import annotations

import os

import httpx

from app.domain import Assessment, Booking

LEADS = {
    "allow": "This booking can proceed to payment and the label.",
    "step-up": "Ask the booker to prove they control this account, then confirm again. Do not print the label yet.",
    "hold": "Do not capture payment and do not print the label. A reviewer should clear this booking the same day.",
    "block": "Refuse this account as the payer. Do not capture payment and do not print the label.",
}

SENTENCES = {
    "ACCOUNT_CLOSED": "The billed account is closed.",
    "INBOUND_POLICY_DENY": "This account refuses third-party and receiver billing, and this shipper is not on the exception list.",
    "NEW_PAYER_RELATIONSHIP": "This shipper has not billed this account before, and the origin is outside the account’s usual ship-from footprint.",
    "ORIGIN_LANE_SHIFT": "The origin is new for this account, the service is express or international, and the account’s history is domestic ground.",
    "VELOCITY_SPIKE": "Bookings in the last hour are far above this account’s weekly pace.",
    "UNLINKED_ACCOUNT_ON_GUEST": "A guest session is billing an account that is not linked to the current login.",
    "THIN_HISTORY": "This account has little history, so a deviation is a step-up rather than a block.",
    "CARD_PAYMENT_OUT_OF_SCOPE": "The payer is a card. This check scores account-billed shipments.",
    "MODEL_ELEVATED_SCORE": "The five rules did not fire. The model score is high against this account’s usual weight and pace, so a person holds it. A score alone never blocks.",
    "ACCOUNT_UNKNOWN": "This account number is not in the master snapshot, so the booking cannot be compared with a history.",
}


def explain(assessment: Assessment, booking: Booking, score: float) -> tuple[str, str]:
    text = template_explanation(assessment, booking, score)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return text, "rules"
    try:
        rewritten = _llm_note(api_key, text, assessment, score)
    except Exception:
        return text, "rules"
    return rewritten or text, "llm" if rewritten else "rules"


def template_explanation(assessment: Assessment, booking: Booking, score: float) -> str:
    who = booking.billed_account or "a card"
    parts = [LEADS[assessment.decision]]
    if assessment.reason_codes:
        details = " ".join(SENTENCES[code] for code in assessment.reason_codes if code in SENTENCES)
        parts.append(details)
    facts = assessment.summary_facts
    if "weekly_pace" in facts:
        parts.append(
            f"Account {who} ({facts.get('account_name', '')}) ships about {facts['weekly_pace']:g} times a week, "
            f"median weight {facts['median_weight_kg']:g} kg. "
            f"This attempt is number {facts['recent_bookings_1h']} in the last hour "
            f"(hold line {facts['velocity_limit_1h']})."
        )
    parts.append(f"Score {score:.2f}. Action chosen by policy {assessment.decision}.")
    return " ".join(parts)


def _llm_note(api_key: str, draft: str, assessment: Assessment, score: float) -> str | None:
    """Optional rewrite. The model must keep the same action and the same reason codes."""
    model = os.environ.get("LLM_MODEL", "gpt-4.1-mini")
    prompt = (
        "Rewrite the draft as three short sentences for a fraud analyst. "
        "Keep the same action and cite every reason code by name. "
        "Do not change the decision. Do not add a new action.\n\n"
        f"Decision: {assessment.decision}\n"
        f"Reason codes: {', '.join(assessment.reason_codes) or 'none'}\n"
        f"Score: {score:.2f}\n"
        f"Draft: {draft}"
    )
    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": "You explain a fraud decision that has already been made."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=6.0,
    )
    response.raise_for_status()
    body = response.json()
    text = body["choices"][0]["message"]["content"].strip()
    return text or None
