"""
Animated logo opener, 1080x1920.

Writes transparent PNG frames of the logo only. At build time these are
composited over the client's own animated backdrop, so the background motion is
the official asset rather than anything invented here. The secondary brand mark
is not drawn separately: a client backdrop normally carries its own already,
and doubling it looks like a mistake.

Compliance: the logo is only scaled uniformly and cross-faded. It is never
rotated, recoloured, re-proportioned or partially obscured.
"""

import os
import fitz
from PIL import Image

W, H = 1080, 1920
FPS = 25
DUR = 3.2
N = int(DUR * FPS)

import brandkit as BK

PRIMARY = BK.PRIMARY
ROOT = BK.PROJECT
LOGO_PDF = BK.LOGO_MAIN
OUT = os.path.join(ROOT, "opener")
os.makedirs(OUT, exist_ok=True)

BASE_W = 760  # logo width at rest


def trim(img):
    b = img.split()[-1].getbbox()
    return img.crop(b) if b else img


def raster_logo(width):
    doc = fitz.open(LOGO_PDF)
    page = doc[0]
    z = width / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(z, z), alpha=True)
    img = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples)
    doc.close()
    return trim(img)


def ease_out(t):
    return 1 - pow(1 - t, 3)


# Rasterise once at high resolution, then downsample per frame (keeps edges clean).
MASTER = raster_logo(BASE_W * 2)

for i in range(N):
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Logo: uniform scale 0.94 -> 1.0 with a fade, settling by 1.0s
    lt = ease_out(min(1.0, i / (1.0 * FPS)))
    scale = 0.94 + 0.06 * lt
    alpha = min(1.0, i / (0.5 * FPS))

    # tail fade-out over the last 0.4s
    tail_start = N - int(0.4 * FPS)
    if i >= tail_start:
        alpha *= max(0.0, 1 - (i - tail_start) / (0.4 * FPS))

    lw = int(BASE_W * scale)
    lg = MASTER.resize((lw, int(MASTER.height * lw / MASTER.width)), Image.LANCZOS)
    if alpha < 1.0:
        a = lg.split()[-1].point(lambda p: int(p * alpha))
        lg.putalpha(a)
    frame.alpha_composite(lg, ((W - lg.width) // 2, (H - lg.height) // 2))

    frame.save(os.path.join(OUT, "f%04d.png" % i))

print("wrote %d frames to %s" % (N, OUT))
