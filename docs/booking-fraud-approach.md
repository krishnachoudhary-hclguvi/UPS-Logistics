# Where the booking fraud engine starts

## Decision

Build a **synchronous risk check on account-billed shipments, at the moment the shipper confirms and before a label or tracking number is issued.**

Start with **rules plus the billed account’s own shipping history**, running in **shadow mode**. Do not start with a general anomaly model, and do not put a language model on the booking path.

The fraud in this problem is not “a weird package.” It is **someone booking freight on a legitimate shipper’s account**. UPS already removes those charges after the real shipper disputes them. By then the package has been picked up, sorted, and delivered, so the carrier keeps the operating cost and loses the revenue. The engine exists to stop that acceptance.

## How this UPS page actually books a shipment

The link is the public single-page ship flow:

`https://www.ups.com/ship/single-page?tx=…&loc=en_IN&src=FWS`

That page is one booking session, not the delivery network. Official UPS label creation follows the same order ([Create and Print Shipping Labels](https://www.ups.com/us/en/support/shipping-support/print-shipping-labels)):

1. **Sign in or continue as a guest.** A UPS profile is optional. A shipping account number is a separate credential from the login.
2. **Ship from.** Origin name, phone, and address. This is the footprint a real account usually repeats.
3. **Ship to.** Consignee name and address, commercial or residential.
4. **Package.** Packaging type, weight, dimensions. From India (`loc=en_IN`), an international shipment also collects contents and customs data.
5. **Service.** Ground, express, worldwide, and the add-ons (declared value, signature). Rating returns a price here. Nothing has shipped.
6. **Payment.** Card, or a UPS account: bill shipper, bill receiver, or a third party. This is the step where a stolen or guessed account number is attached to the movement.
7. **Review and confirm.** The shipper sees the summary and commits.
8. **Label.** UPS issues the 1Z tracking number and the label (print at home, email, or drop off at The UPS Store). **This is the point of no return.** Pickup, origin scan, and hub sort follow the label, not the form.

`tx` is the booking-session id. Use it as the idempotency key for the risk decision so a refresh does not create a second outcome. `src=FWS` marks this web channel. The same check must later sit on the Shipping API, WorldShip, and CampusShip, because those channels create the same 1Z. The web page is only the first place to wire it.

UPS already tells account owners to deny unexpected third-party and freight-collect charges and to keep an exception list ([Protect Yourself From Fraud](https://wwwapps.ups.com/us/en/support/shipping-support/legal-terms-conditions/fight-fraud), Billing Center inbound controls). That list is a **policy input** to the engine. It is not a substitute. It only helps shippers who configured it, and it still does not score a booking that looks nothing like the account.

## Where the engine sits

```
Guest or login
    → ship from / ship to / package / service
    → rating and address checks
    → payer selected (card or UPS account)
    → CONFIRM
          │
          ▼
    Booking Risk API          ← the engine
    allow | step-up | hold | block
          │
          ├─ block or hold → no 1Z, no label, no pickup, no sort
          ├─ step-up → verify, then return here
          └─ allow → issue 1Z and label
                        → pickup or drop-off
                        → network movement
                        → delivery
                        → invoice
                        → dispute          ← detection today
```

Call it **inside the confirm action**, in every channel that can mint a label. The response decides whether step 8 is allowed to run.

| If the check runs… | What is still saved | What is already lost |
| --- | --- | --- |
| At confirm, before the 1Z | The whole movement: linehaul, sort, delivery, and the later write-off | Nothing operational. A false hold delays one booking. |
| After the label, before pickup | Some packages that have not been tendered | Labels already in the wild. Drop-offs can still enter the network. |
| In transit | A possible intercept | Most of the operating cost is already incurred. |
| After delivery (today) | Customer goodwill, if the charge is removed | Transportation cost plus unrecovered revenue, plus the investigation. |

GenAI does **not** sit in that box. The confirm call must return in well under a second from precomputed account features and rules. A model call that writes a paragraph happens **after** the decision, for the analyst queue and the audit record.

## What to build first

Scope v1 to one population:

**Shipments whose payer is a UPS account number** (bill shipper, bill receiver, or third party).

Leave pure card payments out. Card fraud is a chargeback problem and a different loss owner. The loss in this brief is the carrier reversing a charge for a shipper who never booked the package.

Two patterns, in this order:

1. **Account-number misuse.** The booker is not the account. They typed a legitimate account number, often as the third party or receiver who “pays.” Detectable from the account’s history without owning the login system. This is the start.
2. **Account takeover.** The booker is logged in as the real UPS ID, but the device, origin, and lane shifted. Needs login and device signals. Build this second, on the same API.

### Slice 0 — shadow decision on the web confirm

No customer is blocked. Every account-billed confirm on the single-page flow is scored and stored.

**Request, one booking:** session `tx`, channel, logged-in UPS ID or guest, payment type, billed account, shipper account if different, ship-from and ship-to country and postal code, residential flag, package count, weight, packaging, service, declared value.

**Account snapshot, already computed overnight:** status, opened date, inbound-charge policy and exception list, ship-from postals used in the last 90 days, destination countries, usual services, typical weight, shipments per week, known third parties who bill this account.

**Five rules, each emitting a stable reason code:**

| Code | Condition | Shadow action that will later be live |
| --- | --- | --- |
| `INBOUND_POLICY_DENY` | Account denies inbound or third-party charges and this shipper is not on the exception list | Block |
| `NEW_PAYER_RELATIONSHIP` | Bill receiver or third party, and this shipper has never billed this account, and ship-from is outside the account footprint | Hold |
| `ORIGIN_LANE_SHIFT` | Ship-from country or postal never seen for this account, and the service is express or international, and the account’s history is domestic ground | Hold |
| `VELOCITY_SPIKE` | Bookings in a short window far above this account’s weekly rate | Hold |
| `UNLINKED_ACCOUNT_ON_GUEST` | Guest session billing an account that is not linked to the current UPS ID | Step-up |

Anything else is `ALLOW` with a low score. A closed or suspended account is a hard block, not a model question.

**Response:** decision, numeric score, reason codes, the feature values that fired, policy version, and the `tx` id. Store the full request and response. That row is the audit record.

**How you know slice 0 worked:** join later billing disputes (“I did not ship this”) back to these decisions. Precision matters more than recall. The business already lives with missed fraud. It cannot live with innocent shippers held at confirm.

### Slice 1 — act, narrowly

Turn on live actions only for `INBOUND_POLICY_DENY` (the account owner already asked for this) and for holds that a person can clear the same day. Default the rest to step-up, not block.

Step-up should reuse a check the real account owner can pass and a stranger usually cannot: postal code on the account plus a figure from a recent invoice. UPS already uses invoice details to prove account ownership when linking an account. Do not invent a new identity system.

### Slice 2 — score, then explain

When disputes and analyst outcomes exist, fit a model **on the same features the rules use**. Keep the policy rules as overrides. The model’s job is the gray band between obvious misuse and a normal shipper, not the deny-list.

Only then add GenAI. It receives the reason codes and feature values and writes a short note for the analyst: what changed versus this account’s history, and which action the policy already chose. The note is stored with the decision id. It does not choose the action. If the model is unavailable, the reason codes still stand.

## Action framework

| Situation | Action | What the booker sees | What ops does |
| --- | --- | --- | --- |
| Matches the account’s normal origin, lane, service, and pace | Allow | Label, as today | Tender the package |
| Guest using an account they have not linked | Step-up | Prove control of the account, then confirm again | Nothing until the label exists |
| New payer relationship, new origin, or a velocity spike | Hold | “We need to review this shipment before issuing a label.” | No 1Z, no pickup order |
| Inbound policy denies this shipper, or the account is closed | Block | Payment with that account is refused | No 1Z |
| Card payment, v1 | Allow | Unchanged | Out of scope until account-billed fraud is measured |

Holds expire into a recorded analyst decision: release, request verification, or block. Every transition stores who, when, the policy version, and the reason codes. That is the compliance trail. A dashboard for prevented loss comes after these decisions exist; loss avoided is `hold or block` that a later review confirms was fraud, priced at the rated charge plus a standard handling cost. Do not show a dollar figure before that review, or the metric will count false positives as savings.

## False-positive control

The same goodwill this project protects is what a bad block spends.

- An account’s own history is the baseline. A shipper who always sends worldwide express is not suspicious for sending worldwide express.
- The inbound exception list and known ship-from postals are allow-signals, not just deny-signals.
- Live mode starts at step-up and hold. Block is for explicit policy (deny list, closed account), not for a high model score.
- Thresholds are per account, not global.
- Slice 0 stays in shadow until disputed shipments show the holds would have been right often enough to turn on.

## Integration, in the order you need it

1. **Booking confirm** on the single-page flow. One synchronous call. Fail open to allow only while in shadow; once live, fail closed to hold for account-billed shipments if the risk service is down. Failing open in production recreates today’s loss.
2. **Account master and inbound-charge preferences.** Without these, the best rule cannot fire.
3. **Shipment history** for the 90-day snapshot. This is the feature store. Key it by billed account number.
4. **Billing disputes.** Delayed labels. This is how the shadow mode is graded.
5. **Analyst queue** in the fraud workflow, not a new shipping UI.
6. **Other label channels** (Shipping API, WorldShip, CampusShip, mobile) on the same contract. A fraudster who is blocked on the website will switch channel the same day.

## What not to start with

- A model trained on “anomaly” with no dispute labels. Early fraud looks rare and the false-positive cost is a delayed legitimate shipment.
- An LLM that decides allow or block. It is slow, non-repeatable, and hard to audit. Explanations come after reason codes.
- A dashboard. There is nothing to trend until decisions and dispute joins exist.
- Card fraud, claims fraud, or pickup-agent theft. Different events, different owners.
- Every channel at once. Prove the decision on the web confirm, then copy the same call to the API that mints labels.

## First implementation slice

One service, one endpoint, no UI:

`POST /v1/booking-risk`

Input is the confirm payload above. Output is decision, score, reason codes, and policy version. Persistence is one assessment table. Account snapshots are a batch table rebuilt from shipment history. Rules are the five codes in slice 0. The single-page confirm calls this and, for now, **ignores the decision except to log it.**

That is the start. Everything in the solution brief (scores, analyst explanations, block and hold, prevented-loss reporting) hangs off this response. None of it is useful until the confirm step can ask the question and a later dispute can grade the answer.
