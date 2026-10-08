"""
Build 1080x1920 title, question and end cards from brand.json.

Generic brand rules, which nearly every corporate guide states in some form:
  - Stick to the palette. Primary, black and white carry almost everything.
  - On the primary colour use the reverse/outline logo; on black or white use
    the positive one. Getting this backwards is the most common violation.
  - Respect minimum clear space. Guides express it as a fraction of the logo
    plate height (one client's is the height of the "e", about 0.48). Set
    logo.clear_space_ratio above the client's minimum; the code asserts it.
  - Never rotate, recolour or re-proportion the logo.

Read the client's actual guide before the first build and record anything
unusual in the project README. These defaults are a safe starting point, not a
substitute for it.
"""

import os
import fitz
from PIL import Image, ImageDraw, ImageFont

import brandkit as BK
import brandtext as BT

W, H = 1080, 1920
PRIMARY = BK.PRIMARY
BLACK = BK.BLACK
WHITE = BK.WHITE
MUTED = BK.MUTED

OUT = os.path.join(BK.PROJECT, "cards")
os.makedirs(OUT, exist_ok=True)

CLEAR_SPACE_RATIO = BK.LOGO_CLEAR_RATIO


def logo(variant, target_w):
    """Rasterise the vector logo at the exact width needed.

    Always render vector at final size rather than scaling a PNG: at 1080 wide
    a supplied raster is usually too small and the wordmark goes soft.
    """
    src = {"main": BK.LOGO_MAIN, "reverse": BK.LOGO_REVERSE}[variant]
    if not src or not os.path.exists(src):
        raise SystemExit("logo.%s missing from brand.json or not on disk" % variant)
    if src.lower().endswith((".png", ".jpg", ".jpeg")):
        img = Image.open(src).convert("RGBA")
        ratio = target_w / img.width
        img = img.resize((target_w, max(1, int(img.height * ratio))), Image.LANCZOS)
        return trim_alpha(img)
    doc = fitz.open(src)
    page = doc[0]
    zoom = target_w / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=True)
    img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    doc.close()
    return trim_alpha(img)


def trim_alpha(img):
    bbox = img.split()[-1].getbbox()
    return img.crop(bbox) if bbox else img


def device_mark(target_w, colour, opacity):
    """Client's secondary mark, used oversized and faded as a graphic device.

    Returns None when the client has no such mark, in which case the question
    cards are plain colour, which is fine.
    """
    src = BK.DEVICE
    if not src or not os.path.exists(src):
        return None
    bm = Image.open(src).convert("RGBA")
    bm = trim_alpha(bm)
    ratio = target_w / bm.width
    bm = bm.resize((target_w, max(1, int(bm.height * ratio))), Image.LANCZOS)
    flat = Image.new("RGBA", bm.size, colour + (0,))
    a = bm.split()[-1].point(lambda p: int(p * opacity))
    flat.putalpha(a)
    return flat


def centre(draw, text, size, weight, total_w):
    return (total_w - BT.text_length(draw, text, size, weight)) / 2


def place_logo(img, variant, width, margin_side, bottom=200):
    """bottom margin is generous so the logo clears platform UI overlays."""
    lg = logo(variant, width)
    clear = int(lg.height * CLEAR_SPACE_RATIO)
    x = margin_side
    y = H - bottom - lg.height
    # verify clear space is respected against both edges
    assert x >= clear and (H - (y + lg.height)) >= clear, "logo clear space violated"
    img.alpha_composite(lg, (x, y))
    return lg


def question_card(index, eyebrow, text, path):
    img = Image.new("RGBA", (W, H), PRIMARY + (255,))

    # the client's mark, oversized and faded, bleeding off the bottom right
    bm = device_mark(int(W * 1.25), WHITE, BK.DEVICE_OPACITY)
    if bm is not None:
        img.alpha_composite(bm, (int(W * 0.10), int(H * 0.62)))

    d = ImageDraw.Draw(img)
    margin = 96
    max_w = W - margin * 2

    # eyebrow
    BT.draw_text(d, (margin, 430), eyebrow.upper(), 34, 700, BLACK)

    # index rule
    d.rectangle([margin, 502, margin + 96, 510], fill=BLACK)

    # question
    size, lines, line_h = BT.fit_block(d, text, max_w, 740, start=104, weight=800)
    y = 570
    for ln in lines:
        BT.draw_text(d, (margin, y), ln, size, 800, BLACK)
        y += line_h

    # reverse logo on the primary colour, per every guide I have read
    place_logo(img, "reverse", 300, margin)
    img.convert("RGB").save(path, quality=96)
    print("wrote", os.path.basename(path), "| size", size, "|", len(lines), "lines")


def title_card(path, eyebrow=None):
    """Transparent artwork. Composited at build time over the client's own
    animated backdrop, so no background is drawn here."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    d = ImageDraw.Draw(img)
    margin = 96
    copy = BK.COPY

    BT.draw_text(d, (margin, 640), eyebrow or copy.get("title_eyebrow", ""),
                 34, 700, PRIMARY)

    y = 700
    for ln in copy.get("title_lines", [BK.CLIENT]):
        BT.draw_text(d, (margin, y), ln, 122, 800, WHITE)
        y += int(122 * 1.08)

    d.rectangle([margin, 1010, margin + 96, 1018], fill=PRIMARY)

    for i, ln in enumerate(copy.get("strapline", [])):
        BT.draw_text(d, (margin, 1070 + i * 58), ln, 44, 500, MUTED)

    place_logo(img, "main", 300, margin)
    img.save(path)
    print("wrote", os.path.basename(path))


def logo_plate(path, width=760):
    """Transparent full-frame logo plate, reference for the animated opener."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lg = logo("main", width)
    img.alpha_composite(lg, ((W - lg.width) // 2, (H - lg.height) // 2))
    img.save(path)
    print("wrote", os.path.basename(path), lg.size)


def end_card(path):
    """Transparent artwork, composited over the client's backdrop at build."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lg = logo("main", 560)
    img.alpha_composite(lg, ((W - lg.width) // 2, 840))
    d = ImageDraw.Draw(img)
    t = BK.COPY.get("end_text", BK.EVENT or BK.CLIENT)
    BT.draw_text(d, (centre(d, t, 42, 600, W), 840 + lg.height + 70), t, 42, 600, MUTED)
    img.save(path)
    print("wrote", os.path.basename(path))


if __name__ == "__main__":
    # The eyebrow reads just "Question", never "Question Two". Numbering a
    # splash implies an order the viewer cannot see once a clip is cut down or
    # reshared on its own.
    eyebrow = BK.COPY.get("question_eyebrow", "Question")

    logo_plate(os.path.join(OUT, "00_logo.png"))
    title_card(os.path.join(OUT, "01_title.png"))
    alt = BK.COPY.get("title_eyebrow_alt")
    if alt:
        title_card(os.path.join(OUT, "01_title2.png"), alt)
    for q in BK.QUESTIONS:
        question_card(q["id"], q.get("eyebrow", eyebrow), q["text"],
                      os.path.join(OUT, "%s.jpg" % q["id"]))
    end_card(os.path.join(OUT, "99_end.png"))
    BT.report()
