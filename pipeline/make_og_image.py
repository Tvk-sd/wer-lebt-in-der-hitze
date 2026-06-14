"""Generate the OpenGraph social-preview image (1200×630) — a Rothko-style
warm field with the title, matching the site hero. Output: site/og-image.png
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "site" / "og-image.png"
W, H = 1200, 630
INK = (18, 18, 18)

FONT_CANDIDATES = {
    "serif_bold": [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ],
    "sans": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
}


def load(kind, size):
    for path in FONT_CANDIDATES[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rothko_field():
    """Vertical orange→red gradient with a soft glowing top field."""
    img = Image.new("RGB", (W, H), (214, 50, 9))
    px = img.load()
    top = (243, 168, 40)     # orange
    bottom = (210, 40, 8)    # deep red
    for y in range(H):
        t = min(1.0, y / (H * 0.72))
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def main():
    img = rothko_field()
    d = ImageDraw.Draw(img)
    m = 90

    kicker = load("sans", 30)
    title = load("serif_bold", 96)
    sub = load("serif_bold", 38)

    d.text((m, 90), "EINE BERLINER DATENGESCHICHTE", font=kicker, fill=INK)
    d.text((m, 200), "Wer lebt in", font=title, fill=INK)
    d.text((m, 300), "der Hitze?", font=title, fill=INK)
    d.text((m, 452), "Hitze, Baumkronen und Sozialstatus", font=sub, fill=INK)
    d.text((m, 500), "in Berlins 542 Planungsräumen", font=sub, fill=INK)

    img.save(OUT, "PNG", optimize=True)
    print(f"Wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
