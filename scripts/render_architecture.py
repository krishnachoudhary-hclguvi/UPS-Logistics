"""One-page picture of the eight confirm steps."""

from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1350
OUT = "/workspace/docs/architecture.png"

CREAM = (246, 241, 232)
INK = (28, 20, 16)
BROWN = (42, 28, 22)
GOLD = (226, 163, 27)
GOLD_TEXT = (140, 94, 16)
WHITE = (255, 252, 248)
LINE = (230, 217, 200)
MUTED = (111, 100, 92)


def font(kind, size):
    path = {
        "reg": "/usr/share/fonts/truetype/macos/Inter-Regular.ttf",
        "bold": "/usr/share/fonts/truetype/macos/Inter-Bold.ttf",
    }[kind]
    return ImageFont.truetype(path, size)


def text_wh(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def center(draw, box, text, fnt, fill):
    x0, y0, x1, y1 = box
    tw, th = text_wh(draw, text, fnt)
    draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2), text, font=fnt, fill=fill)


def main():
    img = Image.new("RGB", (W, H), CREAM)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 14, H), fill=GOLD)
    draw.text((56, 36), "ARCHITECTURE", font=font("bold", 18), fill=GOLD_TEXT)
    draw.text((56, 68), "Eight steps inside the confirm call.", font=font("bold", 42), fill=INK)
    draw.text(
        (56, 128),
        "The label prints only after allow. The note does not choose the action.",
        font=font("reg", 22),
        fill=MUTED,
    )

    steps = [
        ("1", "Booking", "Form becomes one request"),
        ("2", "Account snapshot", "History and deny-list"),
        ("3", "Rules", "Reason codes"),
        ("4", "Score", "XGBoost, same facts"),
        ("5", "Policy", "Block, hold, step-up, allow"),
        ("6", "Audit log", "Assessment + reason rows"),
        ("7", "Explanation", "Sentences from the codes"),
        ("8", "Review", "Release, uphold, or block"),
    ]
    gap = 18
    left, right = 56, W - 56
    width = (right - left - gap * 3) / 4
    height = 210
    top = 220
    for i, (num, title, body) in enumerate(steps):
        col, row = i % 4, i // 4
        x = left + col * (width + gap)
        y = top + row * (height + 70)
        fill = BROWN if i == 4 else WHITE
        title_fill = (247, 241, 232) if i == 4 else INK
        body_fill = (228, 213, 196) if i == 4 else MUTED
        num_fill = GOLD if i == 4 else GOLD_TEXT
        outline = None if i == 4 else LINE
        draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=fill, outline=outline, width=2)
        draw.text((x + 22, y + 22), num, font=font("bold", 18), fill=num_fill)
        draw.text((x + 22, y + 58), title, font=font("bold", 26), fill=title_fill)
        draw.text((x + 22, y + 110), body, font=font("reg", 20), fill=body_fill)
        if col < 3:
            ax = x + width + 2
            ay = y + height / 2
            draw.polygon([(ax, ay - 8), (ax + 14, ay), (ax, ay + 8)], fill=GOLD)

    tables = [
        ("accounts", "Pace, weight, deny-list"),
        ("account_postals", "Ship-from towns"),
        ("account_users", "Linked logins"),
        ("account_parties", "Who may bill the account"),
        ("booking_attempts", "Labels this hour"),
        ("assessments", "The decision"),
        ("assessment_reasons", "One row per code"),
        ("reviews", "The person’s later action"),
    ]
    draw.text((56, 760), "TABLES", font=font("bold", 16), fill=GOLD_TEXT)
    tw = (right - left - gap * 3) / 4
    th = 100
    for i, (name, body) in enumerate(tables):
        col, row = i % 4, i // 4
        x = left + col * (tw + gap)
        y = 800 + row * (th + 16)
        draw.rounded_rectangle((x, y, x + tw, y + th), radius=14, fill=WHITE, outline=LINE, width=2)
        draw.text((x + 16, y + 16), name, font=font("bold", 18), fill=INK)
        draw.text((x + 16, y + 50), body, font=font("reg", 16), fill=MUTED)

    img.save(OUT, "PNG")
    print(OUT)


if __name__ == "__main__":
    main()
