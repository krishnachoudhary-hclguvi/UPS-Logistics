"""Render the booking-risk system flow as a 16:9 PNG."""

from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1350
OUT = "/workspace/docs/system-flow.png"

CREAM = (246, 241, 232)
INK = (28, 20, 16)
INK_SOFT = (58, 49, 43)
BROWN = (42, 28, 22)
GOLD = (226, 163, 27)
GOLD_TEXT = (140, 94, 16)
WHITE = (255, 252, 248)
LINE = (230, 217, 200)
MUTED = (111, 100, 92)
GREEN = (27, 107, 69)
PALE_GREEN = (231, 243, 236)
AMBER = (143, 94, 12)
PALE_AMBER = (251, 243, 228)
RED = (142, 52, 46)
PALE_RED = (248, 235, 232)
BLUE = (26, 74, 114)
PALE_BLUE = (232, 240, 246)

REG = ImageFont.truetype("/usr/share/fonts/truetype/macos/Inter-Regular.ttf", 22)
MED = ImageFont.truetype("/usr/share/fonts/truetype/macos/Inter-Medium.ttf", 22)
SEMI = ImageFont.truetype("/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf", 22)
BOLD = ImageFont.truetype("/usr/share/fonts/truetype/macos/Inter-Bold.ttf", 22)


def font(kind, size):
    path = {
        "reg": "/usr/share/fonts/truetype/macos/Inter-Regular.ttf",
        "med": "/usr/share/fonts/truetype/macos/Inter-Medium.ttf",
        "semi": "/usr/share/fonts/truetype/macos/Inter-SemiBold.ttf",
        "bold": "/usr/share/fonts/truetype/macos/Inter-Bold.ttf",
    }[kind]
    return ImageFont.truetype(path, size)


def text_wh(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def center_text(draw, box, text, fnt, fill, dy=0):
    x0, y0, x1, y1 = box
    tw, th = text_wh(draw, text, fnt)
    x = x0 + (x1 - x0 - tw) / 2
    y = y0 + (y1 - y0 - th) / 2 + dy
    draw.text((x, y), text, font=fnt, fill=fill)


def round_rect(draw, box, radius, fill, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow_right(draw, x, y, color=GOLD):
    draw.polygon([(x, y - 8), (x + 14, y), (x, y + 8)], fill=color)


def main():
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 14, H), fill=GOLD)

    draw.text((56, 40), "SYSTEM FLOW", font=font("bold", 18), fill=GOLD_TEXT)
    draw.text((56, 72), "The risk check sits inside the confirm call.", font=font("bold", 42), fill=INK)
    draw.text(
        (56, 132),
        "Payment is captured and the label is issued only after Allow.",
        font=font("reg", 22),
        fill=MUTED,
    )

    # Booking steps
    steps = [
        ("1", "Ship from", "Origin", False),
        ("2", "Ship to", "Destination", False),
        ("3", "Package & service", "Weight, lane, price", False),
        ("4", "Payer chosen", "UPS account or card", False),
        ("5", "Confirm", "Risk check runs here", True),
    ]
    gap = 28
    left = 56
    right = W - 56
    usable = right - left
    pill_w = (usable - gap * 4) / 5
    pill_h = 118
    pill_y = 196
    for i, (num, title, sub, hot) in enumerate(steps):
        x = left + i * (pill_w + gap)
        box = (x, pill_y, x + pill_w, pill_y + pill_h)
        if hot:
            round_rect(draw, box, 18, BROWN)
            num_fill, title_fill, sub_fill = GOLD, (247, 241, 232), (228, 213, 196)
        else:
            round_rect(draw, box, 18, WHITE, LINE, 2)
            num_fill, title_fill, sub_fill = GOLD_TEXT, INK, MUTED
        draw.text((x + 22, pill_y + 18), num, font=font("bold", 16), fill=num_fill)
        draw.text((x + 22, pill_y + 42), title, font=font("bold", 24), fill=title_fill)
        draw.text((x + 22, pill_y + 76), sub, font=font("reg", 18), fill=sub_fill)
        if i < 4:
            arrow_right(draw, x + pill_w + 7, pill_y + pill_h / 2)

    # Down arrow from Confirm into the engine
    confirm_x = left + 4 * (pill_w + gap) + pill_w / 2
    draw.line((confirm_x, pill_y + pill_h, confirm_x, 360), fill=GOLD, width=4)
    draw.polygon(
        [(confirm_x - 9, 352), (confirm_x + 9, 352), (confirm_x, 368)],
        fill=GOLD,
    )

    # Engine
    engine = (56, 376, W - 56, 700)
    round_rect(draw, engine, 22, BROWN)
    draw.text((88, 400), "BOOKING RISK CHECK", font=font("bold", 18), fill=GOLD)
    draw.text(
        (88, 432),
        "Inside confirm, before the charge and before the 1Z.",
        font=font("semi", 26),
        fill=(247, 241, 232),
    )
    draw.text(
        (88, 474),
        "Reads this booking, that account’s 90-day history, and the inbound deny-list.",
        font=font("reg", 20),
        fill=(228, 213, 196),
    )

    rules = [
        ("Deny-list hit", "Block", RED, PALE_RED),
        ("New payer", "Hold", AMBER, PALE_AMBER),
        ("New lane", "Hold", AMBER, PALE_AMBER),
        ("Velocity spike", "Hold", AMBER, PALE_AMBER),
        ("Guest, account not linked", "Step-up", BLUE, PALE_BLUE),
    ]
    chip_y = 534
    chip_h = 132
    chip_gap = 18
    chip_left = 88
    chip_right = W - 88
    chip_w = (chip_right - chip_left - chip_gap * 4) / 5
    for i, (name, action, accent, bg) in enumerate(rules):
        x = chip_left + i * (chip_w + chip_gap)
        box = (x, chip_y, x + chip_w, chip_y + chip_h)
        round_rect(draw, box, 16, bg)
        center_text(draw, (x, chip_y + 16, x + chip_w, chip_y + 70), name, font("bold", 20), INK)
        center_text(draw, (x, chip_y + 64, x + chip_w, chip_y + 118), action, font("bold", 26), accent)

    # Outcomes
    outcomes = [
        (GREEN, PALE_GREEN, "ALLOW", "Looks like this account.", "Capture payment. Issue the label.", "Pickup, then delivery."),
        (BLUE, PALE_BLUE, "STEP-UP", "Guest on an unlinked account.", "Prove control of the account.", "Then confirm again. No label yet."),
        (AMBER, PALE_AMBER, "HOLD", "New payer, lane, or velocity.", "No charge and no label.", "A person clears it the same day."),
        (RED, PALE_RED, "BLOCK", "Deny-list, or account closed.", "That account cannot pay.", "No charge and no label."),
    ]
    out_y = 748
    out_h = 250
    out_gap = 22
    out_w = (usable - out_gap * 3) / 4
    for i, (accent, bg, name, a, b, c) in enumerate(outcomes):
        x = left + i * (out_w + out_gap)
        box = (x, out_y, x + out_w, out_y + out_h)
        round_rect(draw, box, 18, bg)
        draw.rectangle((x, out_y, x + out_w, out_y + 8), fill=accent)
        draw.text((x + 28, out_y + 28), name, font=font("bold", 22), fill=accent)
        draw.text((x + 28, out_y + 78), a, font=font("semi", 22), fill=INK)
        draw.text((x + 28, out_y + 118), b, font=font("reg", 20), fill=INK_SOFT)
        draw.text((x + 28, out_y + 156), c, font=font("reg", 20), fill=INK_SOFT)
        # small arrow from engine down to each card
        cx = x + out_w / 2
        draw.line((cx, 708, cx, out_y - 8), fill=LINE, width=3)

    # Footer
    foot = (56, 1032, W - 56, 1272)
    round_rect(draw, foot, 18, WHITE, LINE, 2)
    draw.text((88, 1058), "WHAT CONTINUES, AND WHAT NEVER STARTS", font=font("bold", 16), fill=GOLD_TEXT)
    draw.text(
        (88, 1096),
        "Allow is the only path into the network: label, then pickup or drop-off, then delivery.",
        font=font("semi", 24),
        fill=INK,
    )
    draw.text(
        (88, 1144),
        "Step-up, hold, and block stop in the confirm call. The package is never tendered.",
        font=font("reg", 22),
        fill=INK_SOFT,
    )
    draw.text(
        (88, 1190),
        "Today the same booking is judged after delivery, when the real shipper disputes the invoice.",
        font=font("reg", 22),
        fill=MUTED,
    )

    img.save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
