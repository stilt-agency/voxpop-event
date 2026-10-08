"""
Shared text rendering, brand face with automatic fallback.

Text is drawn as runs, each in the brand face or in a fallback, chosen per
character by what the brand face actually carries.

That machinery exists because trial and web cuts of a corporate typeface are
routinely incomplete. On one job a trial release mapped 68 glyphs and
had no question mark, apostrophe or colon: every question card would have
rendered with holes in it. Ask the client for the full licensed desktop family
and check `report()` says no fallback was used before you sign anything off.

Where a family ships several cuts, match the one the client's own title cards
use rather than assuming the default.
"""

import os
from PIL import ImageFont
from fontTools.ttLib import TTFont

import brandkit as BK

FONTDIR = BK.FONT_DIR
BRAND_FACE = BK.FONT_WEIGHTS
FALLBACK = BK.FONT_FALLBACK

_cover_cache = {}
_font_cache = {}

FALLBACK_USED = set()


def _coverage(path):
    if path not in _cover_cache:
        t = TTFont(path)
        cm = set()
        for tbl in t["cmap"].tables:
            cm |= set(tbl.cmap.keys())
        t.close()
        _cover_cache[path] = cm
    return _cover_cache[path]


def _es_path(weight):
    if not BRAND_FACE:
        raise SystemExit("brand.json has no fonts.weights mapping")
    key = min(BRAND_FACE, key=lambda k: abs(k - weight))
    return os.path.join(FONTDIR, BRAND_FACE[key])


def get_fonts(size, weight=700):
    """Return (primary, fallback) PIL fonts for a size/weight."""
    key = (size, weight)
    if key not in _font_cache:
        primary = ImageFont.truetype(_es_path(weight), size)
        fb = ImageFont.truetype(FALLBACK, size)
        try:
            fb.set_variation_by_axes([weight])
        except Exception:
            pass
        _font_cache[key] = (primary, fb)
    return _font_cache[key]


def split_runs(text, weight=700):
    """Split text into [(chunk, uses_primary)] by brand-face glyph coverage."""
    cov = _coverage(_es_path(weight))
    runs = []
    for ch in text:
        ok = ord(ch) in cov
        if not ok and not ch.isspace():
            FALLBACK_USED.add(ch)
        if runs and runs[-1][1] == ok:
            runs[-1][0] += ch
        else:
            runs.append([ch, ok])
    return [(c, ok) for c, ok in runs]


def text_length(draw, text, size, weight=700):
    primary, fb = get_fonts(size, weight)
    return sum(draw.textlength(c, font=(primary if ok else fb))
               for c, ok in split_runs(text, weight))


def draw_text(draw, xy, text, size, weight=700, fill=(0, 0, 0)):
    """Draw text with per-run font fallback. Returns the advance width."""
    primary, fb = get_fonts(size, weight)
    x, y = xy
    for chunk, ok in split_runs(text, weight):
        f = primary if ok else fb
        draw.text((x, y), chunk, font=f, fill=fill)
        x += draw.textlength(chunk, font=f)
    return x - xy[0]


def wrap(draw, text, size, max_w, weight=700):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_length(draw, trial, size, weight) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_block(draw, text, max_w, max_h, start=104, weight=700, leading=1.14, floor=40):
    size = start
    while size > floor:
        lines = wrap(draw, text, size, max_w, weight)
        line_h = int(size * leading)
        if len(lines) * line_h <= max_h:
            return size, lines, line_h
        size -= 3
    return size, wrap(draw, text, size, max_w, weight), int(size * leading)


def report():
    if FALLBACK_USED:
        chars = " ".join(sorted(FALLBACK_USED))
        print("   [font] the brand face lacks these glyphs, drawn in the "
              "fallback: %s" % chars)
        print("   [font] check you were given the full family, not a trial cut.")
    else:
        print("   [font] the brand face covered every glyph, no fallback used.")
