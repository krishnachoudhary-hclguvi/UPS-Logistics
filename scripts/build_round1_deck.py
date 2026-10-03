"""Build the Round 1 idea and solution-design deck.

Widescreen 16:9. Speaker notes are the 7-minute script.
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

W, H = 13.333, 7.5
FONT = "Calibri"

INK = "1C1410"
INK_SOFT = "3A312B"
BROWN = "2A1C16"
GOLD = "8C5E10"
GOLD_BRIGHT = "E2A31B"
CREAM = "F6F1E8"
WHITE = "FFFcf8"
CARD = "FFFFFF"
LINE = "E6D9C8"
MUTED = "6F645C"
GREEN = "1B6B45"
AMBER = "8F5E0C"
RED = "8E342E"
BLUE = "1A4A72"
PALE_GREEN = "E7F3EC"
PALE_AMBER = "FBF3E4"
PALE_RED = "F8EBE8"
PALE_BLUE = "E8F0F6"
PALE_GOLD = "FBF6EC"


def rgb(hex_color):
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _apply_font(run, name):
    r_pr = run._r.get_or_add_rPr()
    for tag in ("a:latin", "a:ea", "a:cs"):
        node = r_pr.find(qn(tag))
        if node is None:
            node = r_pr.makeelement(qn(tag), {})
            r_pr.append(node)
        node.set("typeface", name)


def add_run(paragraph, text, size, bold=False, color=INK, italic=False, font=FONT):
    run = paragraph.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = rgb(color)
    run.font.name = font
    _apply_font(run, font)
    return run


def textbox(slide, x, y, w, h, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT,
            italic=False, anchor=MSO_ANCHOR.TOP, font=FONT):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    add_run(p, text, size, bold, color, italic, font)
    return shape


def fill_shape(shape, fill, line=None, line_pt=1.0):
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = rgb(line)
        shape.line.width = Pt(line_pt)


def rect(slide, x, y, w, h, fill, line=None, line_pt=1.0, rounded=False, radius=0.08):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    fill_shape(shape, fill, line, line_pt)
    if rounded:
        # adj0 is corner radius as a fraction of the shorter side
        try:
            shape.adjustments[0] = radius
        except Exception:
            pass
    shape.shadow.inherit = False
    return shape


def write(shape, lines, anchor=MSO_ANCHOR.TOP, margin=0.12):
    """lines: list of dicts with keys text, size, bold, color, italic, align, space_before, space_after."""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(0.08)
    tf.margin_bottom = Inches(0.08)
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = line.get("align", PP_ALIGN.LEFT)
        p.space_before = Pt(line.get("before", 0))
        p.space_after = Pt(line.get("after", 0))
        if "spc" in line:
            p.line_spacing = line["spc"]
        add_run(
            p,
            line["text"],
            line.get("size", 14),
            line.get("bold", False),
            line.get("color", INK),
            line.get("italic", False),
        )
    return tf


def notes(slide, script):
    frame = slide.notes_slide.notes_text_frame
    frame.text = script.strip()


def footer(slide, page, total=10, dark=False):
    color = "A89888" if dark else "8A7B70"
    textbox(slide, 0.48, 7.12, 8.5, 0.26,
            "Booking-time fraud detection  ·  Round 1 idea & solution design",
            11, False, color)
    textbox(slide, 11.3, 7.12, 1.55, 0.26, f"{page:02d}  /  {total:02d}",
            11, False, color, align=PP_ALIGN.RIGHT)


def kicker(slide, text, color=GOLD):
    textbox(slide, 0.48, 0.28, 12.2, 0.28, text, 12, True, color)


def title(slide, text, y=0.54, h=0.72, size=30):
    textbox(slide, 0.48, y, 12.3, h, text, size, True, INK)


def content_bg(slide):
    rect(slide, 0, 0, W, H, CREAM)
    rect(slide, 0, 0, 0.12, H, GOLD_BRIGHT)


def new_content(prs, kicker_text, title_text, page, title_h=0.7, title_size=30):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    content_bg(slide)
    kicker(slide, kicker_text)
    title(slide, title_text, h=title_h, size=title_size)
    if page <= 10:
        footer(slide, page)
    return slide


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    prs.core_properties.title = "Stop the shipment before the label exists"
    prs.core_properties.subject = "Round 1 — Idea and solution design review — 3 October 2026"
    prs.core_properties.category = "UPS Logistics booking fraud detection"
    blank = prs.slide_layouts[6]

    # ----- 1. Title -----
    s = prs.slides.add_slide(blank)
    rect(s, 0, 0, W, H, BROWN)
    rect(s, 0, 0, 0.18, H, GOLD_BRIGHT)
    textbox(s, 0.62, 0.42, 10, 0.3,
            "ROUND 1   ·   IDEA & SOLUTION DESIGN REVIEW", 13, True, GOLD_BRIGHT)
    textbox(s, 0.62, 1.55, 12.0, 1.9,
            "Stop the shipment\nbefore the label exists.", 48, True, "F7F1E8")
    rect(s, 0.64, 3.65, 1.7, 0.045, GOLD_BRIGHT)
    textbox(s, 0.62, 3.9, 9.4, 1.05,
            "A real-time fraud check for packages booked on a legitimate\nshipper’s UPS account — at confirm, before the label is issued.",
            20, False, "E4D5C4")

    # three meta chips
    metas = [
        ("3 October 2026", "1:00 PM  ·  25 marks"),
        ("7 minutes", "Presentation"),
        ("3 minutes", "Questions"),
    ]
    for i, (a, b) in enumerate(metas):
        x = 0.62 + i * 3.15
        rect(s, x, 5.55, 2.95, 1.15, "3A2A22", rounded=True, radius=0.12)
        textbox(s, x + 0.2, 5.7, 2.55, 0.42, a, 16, True, "F7F1E8")
        textbox(s, x + 0.2, 6.12, 2.55, 0.36, b, 13, False, "CDBBA6")

    notes(s, """
[0:00 – 0:20]

People are booking packages on a legitimate shipper’s account. Today that is found after delivery, when the carrier has already paid for the trip.

We put a risk check on the confirm step, before the label exists. Problem, where it sits, the approach, the build, and the impact.

[Add team names on this slide before you present.]
""")

    # ----- 2. Problem -----
    s = new_content(prs, "PROBLEM UNDERSTANDING",
                    "The package is delivered before the fraud is named.", 2)
    steps = [
        ("01", "Booked on a real identity",
         "A fraudulent shipper uses a legitimate account number, login, or payment identity to create the shipment."),
        ("02", "Found only after delivery",
         "Detection today is shipping-pattern analysis and related signals — after the package has moved."),
        ("03", "The carrier keeps the loss",
         "The real shipper is protected and the charge is removed. Goodwill survives. Revenue and operating cost do not."),
    ]
    for i, (num, head, body) in enumerate(steps):
        y = 1.5 + i * 1.65
        card = rect(s, 0.48, y, 12.35, 1.5, CARD, LINE, 1.0, rounded=True, radius=0.08)
        write(card, [
            {"text": num, "size": 14, "bold": True, "color": GOLD, "before": 2},
            {"text": head, "size": 22, "bold": True, "color": INK, "before": 2},
            {"text": body, "size": 15, "color": INK_SOFT, "before": 4},
        ], margin=0.28)
    notes(s, """
[0:20 – 1:05]

Three steps. Someone books with a real shipper’s account. The label prints, and the package is picked up, sorted, and delivered.

It is named after delivery — from the shipping pattern, or when the real shipper says, “I did not ship this.”

The carrier removes the charge. The customer is protected. The freight revenue and the cost of the movement stay with the carrier.

We need a decision before the package moves.
""")

    # ----- 3. Industry -----
    s = new_content(prs, "INDUSTRY RELEVANCE",
                    "The industry stops the invoice. It does not stop the booking.", 3,
                    title_h=0.85, title_size=28)
    left = rect(s, 0.48, 1.7, 6.05, 4.95, CARD, LINE, 1.0, rounded=True, radius=0.06)
    right = rect(s, 6.75, 1.7, 6.08, 4.95, BROWN, rounded=True, radius=0.06)
    write(left, [
        {"text": "WHAT CARRIERS ALREADY DO", "size": 12, "bold": True, "color": GOLD, "before": 0},
        {"text": "Protect account numbers and investigate irregular charges.", "size": 16, "color": INK, "before": 14},
        {"text": "Let shippers deny inbound and third-party billing, with an exception list.", "size": 16, "color": INK, "before": 12},
        {"text": "Remove incorrect charges after a dispute, to keep the customer.", "size": 16, "color": INK, "before": 12},
        {"text": "Use trend analysis once shipments have already moved.", "size": 16, "color": INK, "before": 12},
    ], anchor=MSO_ANCHOR.MIDDLE, margin=0.32)
    write(right, [
        {"text": "WHAT IS STILL OPEN", "size": 12, "bold": True, "color": GOLD_BRIGHT, "before": 0},
        {"text": "A yes or no at the moment of booking.", "size": 16, "color": "F7F1E8", "before": 14},
        {"text": "A comparison with that account’s own history, not a network average.", "size": 16, "color": "F7F1E8", "before": 12},
        {"text": "A hold before pickup, sort, and delivery.", "size": 16, "color": "F7F1E8", "before": 12},
        {"text": "Enforcement of the deny-list even when the booker never asks.", "size": 16, "color": "F7F1E8", "before": 12},
    ], anchor=MSO_ANCHOR.MIDDLE, margin=0.32)
    notes(s, """
[1:05 – 1:45]

This is already an industry problem. Carriers protect account numbers, investigate bad charges, and take incorrect invoices off the account. Shippers can deny inbound and third-party billing.

Those controls sit on the invoice, or in a preference the shipper has to turn on. The package has moved, or the control never fires.

The gap is the booking moment. On the public UPS ship page, nothing is in the network until confirm issues the label.
""")

    # ----- 4. Where it sits -----
    s = new_content(prs, "WHERE THE ENGINE SITS",
                    "Confirm is the last moment the package is still an idea.", 4,
                    title_h=0.7, title_size=28)
    pills = [
        ("Ship from", False),
        ("Ship to", False),
        ("Package\n& service", False),
        ("Bill a UPS\naccount", False),
        ("Confirm", True),
        ("Label / 1Z", False),
    ]
    pill_w, gap, pill_y, pill_h = 1.9, 0.12, 1.55, 0.78
    start_x = 0.48
    for i, (label, hot) in enumerate(pills):
        x = start_x + i * (pill_w + gap)
        if hot:
            shape = rect(s, x, pill_y, pill_w, pill_h, BROWN, rounded=True, radius=0.15)
            write(shape, [{"text": label, "size": 14, "bold": True, "color": GOLD_BRIGHT, "align": PP_ALIGN.CENTER}],
                  anchor=MSO_ANCHOR.MIDDLE, margin=0.06)
        elif i == 5:
            shape = rect(s, x, pill_y, pill_w, pill_h, CREAM, "C4B5A4", 1.25, rounded=True, radius=0.15)
            shape.line.dash_style = MSO_LINE.DASH
            write(shape, [{"text": label, "size": 14, "bold": True, "color": MUTED, "align": PP_ALIGN.CENTER}],
                  anchor=MSO_ANCHOR.MIDDLE, margin=0.06)
        else:
            shape = rect(s, x, pill_y, pill_w, pill_h, CARD, LINE, 1.0, rounded=True, radius=0.15)
            write(shape, [{"text": label, "size": 14, "bold": True, "color": INK, "align": PP_ALIGN.CENTER}],
                  anchor=MSO_ANCHOR.MIDDLE, margin=0.06)
        if i < 5:
            textbox(s, x + pill_w - 0.02, pill_y + 0.18, 0.18, 0.4, "›", 18, True, GOLD, align=PP_ALIGN.CENTER)

    textbox(s, 0.48, 2.48, 12.3, 0.32,
            "The risk check runs inside Confirm. The label is created only after Allow.",
            14, False, MUTED)

    outcomes = [
        (GREEN, PALE_GREEN, "ALLOW", "Looks like this account’s normal origin, lane, service, and pace.", "Label prints."),
        (BLUE, PALE_BLUE, "STEP-UP", "A guest is billing an account they have not linked.", "Prove control, then confirm again."),
        (AMBER, PALE_AMBER, "HOLD", "New payer, new lane, or a burst of bookings.", "No label until a person clears it."),
        (RED, PALE_RED, "BLOCK", "The account denies this shipper, or the account is closed.", "That account cannot pay."),
    ]
    for i, (accent, bg, name, body, foot) in enumerate(outcomes):
        x = 0.48 + i * 3.18
        card = rect(s, x, 2.98, 3.05, 2.55, bg, rounded=True, radius=0.08)
        rect(s, x, 2.98, 3.05, 0.08, accent)
        write(card, [
            {"text": name, "size": 14, "bold": True, "color": accent, "before": 0},
            {"text": body, "size": 14, "color": INK, "before": 8},
            {"text": foot, "size": 13, "bold": True, "color": INK, "before": 8},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.16)

    bar = rect(s, 0.48, 5.7, 12.35, 1.15, BROWN, rounded=True, radius=0.08)
    write(bar, [
        {"text": "Same gate, every channel that can print a label.", "size": 16, "bold": True, "color": "F7F1E8", "before": 4},
        {"text": "Start on the single-page website. Then the Shipping API, WorldShip, CampusShip, and mobile. A block on the website alone just moves the booking.", "size": 14, "color": "E4D5C4", "before": 4},
    ], margin=0.22)
    notes(s, """
[1:45 – 2:35]

Origin, destination, package, service. Rating returns a price. Nothing has shipped. Payment is where a UPS account is attached — shipper, receiver, or third party.

Confirm issues the 1Z and the label. Pickup and sort follow that label. The engine is a synchronous call inside confirm. Allow prints the label. Step-up, hold, and block do not.

The tx on the page is the id we store with the decision. Start on this website, then the same call on the Shipping API and desktop tools. A block on the website alone just moves the booking.
""")

    # ----- 5. Solution map -----
    s = new_content(prs, "SOLUTION DESIGN",
                    "Nine capabilities. Only five sit on the booking path.", 5)
    left = rect(s, 0.48, 1.48, 6.35, 5.4, CARD, LINE, 1.0, rounded=True, radius=0.06)
    right = rect(s, 7.0, 1.48, 5.85, 5.4, CARD, LINE, 1.0, rounded=True, radius=0.06)
    sync_items = [
        ("Real-time fraud detection", "Score the booking before the label exists."),
        ("Behavioral pattern analysis", "Origin, destination, weight, service, timing, frequency."),
        ("Identity and account validation", "Login, guest, and billed account have to belong together."),
        ("Risk scoring model", "Rules first. A learned score once dispute labels exist."),
        ("Action framework", "Allow, step-up, hold, or block — before tender."),
    ]
    async_items = [
        ("GenAI explanation", "Plain language for the analyst, tied to reason codes."),
        ("False-positive control", "Per-account baselines. Shadow mode before live friction."),
        ("Integration", "Booking, account master, payer type, disputes, analyst queue."),
        ("Auditability and compliance", "Decision, features, policy version, and reviewer, stored together."),
    ]
    write(left, [{"text": "ON THE CONFIRM CALL  ·  SYNCHRONOUS", "size": 12, "bold": True, "color": GOLD, "before": 2}], margin=0.22)
    # manual paragraphs via write only did the header; add items as separate textboxes for spacing control
    for i, (name, body) in enumerate(sync_items):
        y = 2.15 + i * 0.88
        textbox(s, 0.78, y, 5.8, 0.32, name, 16, True, INK)
        textbox(s, 0.78, y + 0.30, 5.8, 0.4, body, 13, False, MUTED)
    write(right, [{"text": "AFTER THE DECISION  ·  ASYNCHRONOUS", "size": 12, "bold": True, "color": GOLD, "before": 2}], margin=0.22)
    for i, (name, body) in enumerate(async_items):
        y = 2.15 + i * 1.05
        textbox(s, 7.28, y, 5.3, 0.32, name, 16, True, INK)
        textbox(s, 7.28, y + 0.30, 5.3, 0.5, body, 13, False, MUTED)
    notes(s, """
[2:35 – 3:10]

The brief has nine capabilities. Five have to finish before the label: screen the booking, compare it with this account’s history, check identity against the account, score it, and choose an action.

Four can finish after: the plain-language note, false-positive control, the integrations, and the audit record. GenAI is in that second group. It does not sit in front of the label printer.

Point left, then right. Do not read every line.
""")

    # ----- 6. Innovation -----
    s = new_content(prs, "INNOVATION AND ORIGINALITY",
                    "Four choices that make this specific to this fraud.", 6)
    ideas = [
        ("01", "The victim account is the baseline",
         "Score this booking against this account’s own origins, lanes, services, weight, and weekly pace."),
        ("02", "Shipper policy becomes a live block",
         "The inbound deny-list and exception list already in billing fire at confirm, even if the booker never opted in to a review."),
        ("03", "GenAI explains. It does not decide.",
         "The action comes from rules and the score. The model writes the analyst note and stores it with the same decision id."),
        ("04", "Shadow mode before any friction",
         "Log every decision. Grade it against later disputes. Turn on hold and block only where that evidence is strong."),
    ]
    for i, (num, head, body) in enumerate(ideas):
        col, row = i % 2, i // 2
        x = 0.48 + col * 6.4
        y = 1.5 + row * 2.6
        card = rect(s, x, y, 6.2, 2.42, CARD, LINE, 1.0, rounded=True, radius=0.07)
        write(card, [
            {"text": num, "size": 13, "bold": True, "color": GOLD, "before": 0},
            {"text": head, "size": 18, "bold": True, "color": INK, "before": 6},
            {"text": body, "size": 15, "color": INK_SOFT, "before": 8},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.28)
    notes(s, """
[3:10 – 3:55]

Four choices make this specific.

The baseline is the victim account: its own origins, lanes, services, weight, and weekly pace. A network average flags a busy legitimate exporter and misses a quiet account’s first bad booking.

The deny-list the shipper already has in billing becomes a block at confirm.

The language model writes the analyst note from reason codes. It does not choose the action, so the decision stays repeatable.

And we log in shadow, and grade against later disputes, before any live shipper is held.
""")

    # ----- 7. Technical -----
    s = new_content(prs, "AI / TECHNICAL APPROACH",
                    "Rules decide. A model ranks. GenAI explains.", 7)
    cols = [
        ("INPUTS", [
            "Confirm payload: session, payer, origin, destination, weight, service",
            "Nightly account snapshot: 90-day footprint and weekly pace",
            "Inbound-charge policy and the exception list",
        ]),
        ("DECISION", [
            "Policy rules override everything",
            "Behavioral rules for the gray cases",
            "Gradient-boosted score once dispute labels exist, on the same features",
        ]),
        ("RECORD", [
            "Allow continues to the label",
            "Step-up, hold, or block stops it",
            "Reason codes, feature values, policy version, and the GenAI note",
        ]),
    ]
    for i, (head, bullets) in enumerate(cols):
        x = 0.48 + i * 4.22
        card = rect(s, x, 1.42, 4.05, 3.15, CARD, LINE, 1.0, rounded=True, radius=0.07)
        write(card, [
            {"text": head, "size": 12, "bold": True, "color": GOLD, "before": 0},
            {"text": bullets[0], "size": 14, "color": INK, "before": 12},
            {"text": bullets[1], "size": 14, "color": INK, "before": 10},
            {"text": bullets[2], "size": 14, "color": INK, "before": 10},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.2)

    codes = [
        ("Deny-list hit", "Block", RED, PALE_RED),
        ("New payer relationship", "Hold", AMBER, PALE_AMBER),
        ("Origin or lane shift", "Hold", AMBER, PALE_AMBER),
        ("Velocity spike", "Hold", AMBER, PALE_AMBER),
        ("Guest, account not linked", "Step-up", BLUE, PALE_BLUE),
    ]
    textbox(s, 0.48, 4.7, 8, 0.28, "FIRST FIVE REASON CODES  ·  ACCOUNT-BILLED SHIPMENTS ONLY", 11, True, GOLD)
    for i, (name, action, accent, bg) in enumerate(codes):
        x = 0.48 + (i % 5) * 2.52
        y = 5.08
        chip = rect(s, x, y, 2.42, 1.78, bg, rounded=True, radius=0.1)
        write(chip, [
            {"text": name, "size": 13, "bold": True, "color": INK, "align": PP_ALIGN.CENTER, "before": 0},
            {"text": action, "size": 16, "bold": True, "color": accent, "align": PP_ALIGN.CENTER, "before": 6},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.1)
    notes(s, """
[3:55 – 4:50]

One endpoint, called by confirm. Inputs: the booking, a nightly 90-day snapshot of that account, and the inbound-charge policy.

Five rules. Deny-list or a closed account blocks. A new payer outside the account’s origins holds. A new express or international lane, when this account ships domestic ground, holds. A burst above the weekly pace holds. A guest billing an unlinked account is a step-up.

Account-billed only: shipper, receiver, or third party. Card payments are a different loss.

Later, a gradient-boosted model scores the same features. Rules still override. GenAI turns the codes into a short analyst note, stored with the decision. If the language model is down, the codes still stand.
""")

    # ----- 8. Actions and false positives -----
    s = new_content(prs, "ACTIONS AND FALSE-POSITIVE CONTROL",
                    "Friction scales with how wrong the account looks.", 8, title_size=28)
    controls = [
        ("Per account, not global",
         "An exporter who always sends worldwide express is normal for that account."),
        ("Thin history is a step-up",
         "A new account has no baseline. Missing history is not treated as an anomaly."),
        ("Block is policy, not a score",
         "Auto-block is the deny-list or a closed account. A high score holds for a person."),
        ("Step-up reuses a known proof",
         "Account postal code plus a figure from a recent invoice — the same proof used to link an account today."),
    ]
    for i, (head, body) in enumerate(controls):
        col, row = i % 2, i // 2
        x = 0.48 + col * 6.4
        y = 1.48 + row * 2.15
        card = rect(s, x, y, 6.2, 2.0, CARD, LINE, 1.0, rounded=True, radius=0.08)
        rect(s, x + 0.1, y + 0.18, 0.07, 1.64, GOLD_BRIGHT)
        write(card, [
            {"text": head, "size": 18, "bold": True, "color": INK, "before": 0},
            {"text": body, "size": 15, "color": INK_SOFT, "before": 8},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.32)
    notes(s, """
[4:50 – 5:30]

Thresholds are per account. Express is normal for an account whose history is express.

A new account has no pattern to break. Thin history is a step-up, not a block.

Auto-block is only the deny-list or a closed account. A high score holds for a person.

Step-up reuses a proof UPS already uses to link an account: postal code, plus a figure from a recent invoice. The owner can pass it. A stranger with only the account number usually cannot.

If challenged on customer impact: we would rather miss a fraud in the pilot than hold a legitimate shipper at confirm.
""")

    # ----- 9. Plan -----
    s = new_content(prs, "FEASIBILITY AND IMPLEMENTATION",
                    "The first release logs the decision and stops nobody.", 9, title_size=28)
    phases = [
        ("0", "Shadow", "Web confirm calls the API. Five rules. Full audit row. The shipper sees no change."),
        ("1", "Act", "Step-up and same-day hold go live. Block only on the deny-list and closed accounts."),
        ("2", "Learn", "Model trained on disputes and analyst outcomes. GenAI brief on the same decision id."),
        ("3", "Extend", "The same call on the Shipping API, WorldShip, CampusShip, and mobile."),
    ]
    for i, (num, name, body) in enumerate(phases):
        x = 0.48 + i * 3.2
        circ = rect(s, x, 1.5, 0.48, 0.48, BROWN, rounded=True, radius=0.5)
        write(circ, [{"text": num, "size": 16, "bold": True, "color": GOLD_BRIGHT, "align": PP_ALIGN.CENTER}],
              anchor=MSO_ANCHOR.MIDDLE, margin=0.02)
        if i < 3:
            rect(s, x + 0.55, 1.7, 2.55, 0.045, "E0D2C0")
        textbox(s, x, 2.1, 3.0, 0.36, name, 18, True, INK)
        textbox(s, x, 2.5, 3.0, 1.35, body, 13, False, INK_SOFT)

    need = rect(s, 0.48, 4.15, 8.15, 2.7, CARD, LINE, 1.0, rounded=True, radius=0.07)
    write(need, [
        {"text": "THREE FEEDS, THEN THE PILOT IS REAL", "size": 12, "bold": True, "color": GOLD, "before": 0},
        {"text": "Account master, including inbound-charge preferences.", "size": 15, "color": INK, "before": 12},
        {"text": "90-day shipment history, keyed by the billed account.", "size": 15, "color": INK, "before": 8},
        {"text": "Billing disputes — the label that grades the shadow decisions.", "size": 15, "color": INK, "before": 8},
    ], anchor=MSO_ANCHOR.MIDDLE, margin=0.26)
    out = rect(s, 8.8, 4.15, 4.05, 2.7, BROWN, rounded=True, radius=0.07)
    write(out, [
        {"text": "LEFT FOR LATER", "size": 12, "bold": True, "color": GOLD_BRIGHT, "before": 0},
        {"text": "Card-paid guest shipments.", "size": 15, "color": "F7F1E8", "before": 12},
        {"text": "A dashboard before decisions and dispute joins exist.", "size": 15, "color": "F7F1E8", "before": 8},
        {"text": "Account-takeover device signals. Same API, second pattern.", "size": 15, "color": "F7F1E8", "before": 8},
    ], anchor=MSO_ANCHOR.MIDDLE, margin=0.22)
    notes(s, """
[5:30 – 6:15]

Slice zero is one endpoint, five rules, and a log. Confirm calls it. The shipper sees no change. We can build that on sample bookings before any live hookup.

Then step-up and same-day hold. Then the model and the note, once dispute labels exist. Then the same call on every other channel that prints a label.

Three feeds: account master, 90-day history, and billing disputes. The hard part is the confirm button asking the question, and disputes coming back to grade the answer.
""")

    # ----- 10. Impact -----
    s = prs.slides.add_slide(blank)
    rect(s, 0, 0, W, H, BROWN)
    rect(s, 0, 0, 0.18, H, GOLD_BRIGHT)
    textbox(s, 0.55, 0.28, 12, 0.28, "EXPECTED IMPACT", 12, True, GOLD_BRIGHT)
    textbox(s, 0.55, 0.58, 12.2, 0.7, "A prevented shipment never enters the network.", 30, True, "F7F1E8")

    impacts = [
        ("Revenue", "The charge is never invoiced, so it never has to be reversed."),
        ("Operating cost", "No pickup, linehaul, sort, or delivery for that booking."),
        ("Shipper trust", "The legitimate account is not billed for a stranger’s package."),
        ("Investigation", "The analyst opens a reason, not a raw score."),
    ]
    for i, (head, body) in enumerate(impacts):
        x = 0.55 + (i % 4) * 3.15
        card = rect(s, x, 1.7, 3.0, 2.35, "3A2A22", rounded=True, radius=0.1)
        write(card, [
            {"text": head, "size": 16, "bold": True, "color": GOLD_BRIGHT, "before": 0},
            {"text": body, "size": 15, "color": "F3E6D6", "before": 8},
        ], anchor=MSO_ANCHOR.MIDDLE, margin=0.18)

    measure = rect(s, 0.55, 4.25, 12.25, 2.45, "140E0C", rounded=True, radius=0.06)
    write(measure, [
        {"text": "HOW WE WILL KNOW", "size": 12, "bold": True, "color": GOLD_BRIGHT, "before": 2},
        {"text": "Of shipments later disputed, how many would this gate have held?", "size": 18, "color": "F7F1E8", "before": 10},
        {"text": "Of shipments never disputed, how many would it have held?", "size": 18, "color": "F7F1E8", "before": 4},
        {"text": "Rupees saved are counted only after a review confirms the hold was fraud.", "size": 15, "color": "E4D5C4", "before": 8},
    ], margin=0.28)
    footer(s, 10, dark=True)
    notes(s, """
[6:15 – 7:00]

If the gate works, that package is never tendered. No reversed invoice, no linehaul, and the real shipper never sees the charge. The analyst opens a reason, not a raw score.

No rupee figure. A hold is not a saving until a review confirms it was fraud. Measure two rates: of later disputes, how many we would have held; of clean shipments, how many we would have held.

Prevent the movement. Then explain it.

Stop. Invite questions. The last slide is backup only.
""")

    # ----- 11. Q&A appendix -----
    s = new_content(prs, "APPENDIX  ·  FLIP HERE ONLY IF ASKED",
                    "Short answers for the three minutes.", 11, title_size=28)
    textbox(s, 0.48, 7.12, 8.5, 0.26,
            "Booking-time fraud detection  ·  Round 1 idea & solution design",
            11, False, "8A7B70")
    textbox(s, 10.7, 7.12, 2.15, 0.26, "Appendix", 11, True, GOLD, align=PP_ALIGN.RIGHT)

    qa = [
        ("Why not let the LLM decide?",
         "It is slow, it can change its answer, and it is weak in an audit. Rules decide. The note explains the codes."),
        ("Why not an anomaly model now?",
         "Dispute labels do not exist yet. A network-wide anomaly flags busy legitimate shippers."),
        ("How is this different from the inbound deny-list?",
         "That list is an input. We also catch a booking that uses a valid account in a lane that account has never shipped."),
        ("What if the risk service is down?",
         "In shadow, fail open and log it. Once live, an account-billed confirm with no answer is a hold, not a label."),
        ("What about a new account?",
         "No baseline, so no behavioral block. Step-up or explicit policy only. Thin history is not fraud."),
        ("Where do the labels come from?",
         "Billing disputes — “I did not ship this” — joined back to the decision on the booking session id."),
    ]
    for i, (q, a) in enumerate(qa):
        col, row = i % 2, i // 2
        x = 0.48 + col * 6.4
        y = 1.48 + row * 1.8
        card = rect(s, x, y, 6.2, 1.68, CARD, LINE, 1.0, rounded=True, radius=0.08)
        write(card, [
            {"text": q, "size": 14, "bold": True, "color": INK, "before": 0},
            {"text": a, "size": 13, "color": INK_SOFT, "before": 4},
        ], margin=0.16)
    notes(s, """
Do not present this slide in the 7 minutes. Use it when a question matches.

If the question is not on this page, answer in one breath and bridge back to three points: the gate is on confirm, the baseline is the victim account, and shadow mode comes before any customer friction.

Reason-code names if an engineer asks:
INBOUND_POLICY_DENY → block
NEW_PAYER_RELATIONSHIP → hold
ORIGIN_LANE_SHIFT → hold
VELOCITY_SPIKE → hold
UNLINKED_ACCOUNT_ON_GUEST → step-up

Endpoint: POST /v1/booking-risk
Idempotency key: the tx session id on the ship page.
Population: bill shipper, bill receiver, third party. Card payments are out of version one.
GenAI input: reason codes plus feature gaps. Output stored with the decision id. Never on the synchronous path.

If they ask for a prototype next: slice zero on sample account histories, shadow decisions only.
""")
    return prs


if __name__ == "__main__":
    deck = build()
    out = "/workspace/docs/Round1-Idea-and-Solution-Design.pptx"
    deck.save(out)
    print(out)
