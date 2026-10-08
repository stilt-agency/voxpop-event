"""
Generate the lower-third and caption overlay PNGs for each soundbite.

Both are drawn full-frame at 1080x1920 with transparency so ffmpeg can composite
them at 0,0.

Vertical placement avoids collisions:
  captions only          -> caption block bottom at y 1450
  lower third only       -> plate at y 1400
  both                   -> captions bottom at y 1300, plate at y 1430
"""

import json
import os

from PIL import Image, ImageDraw

import brandkit as BK
import brandtext as BT

ROOT = BK.PROJECT
W, H = 1080, 1920
PRIMARY = BK.PRIMARY
WHITE = BK.WHITE
BLACK = BK.BLACK

LT_DIR = os.path.join(ROOT, "ov_lt")
CAP_DIR = os.path.join(ROOT, "ov_cap")
for d in (LT_DIR, CAP_DIR):
    os.makedirs(d, exist_ok=True)

HEAD_HANDLE = 0.12          # must match build.py
LT_MIN_BITE = 5.0           # do not badge a shot shorter than this

# A lower third is generated for every eligible bite. Which ones actually get
# burned in is decided per programme in build.py, where the rule is one plate
# per person per video, on their first appearance.
LT_DURATION = 4.5
CAP_MAX_CHARS = 52      # ~2 lines at this size, so phrases stay intact
CAP_MAX_WORDS = 9
CAP_MAX_SECS = 3.2


# --------------------------------------------------------------------------- lower third

def lower_third(name, title, company, path, y_top):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    x = 72
    pad_x, pad_y = 34, 26
    name_size, sub_size = 56, 34
    gap = 12

    line2 = "%s at %s" % (title, company) if title else company

    w1 = BT.text_length(d, name, name_size, 700)
    w2 = BT.text_length(d, line2, sub_size, 500)
    plate_w = int(max(w1, w2)) + pad_x * 2 + 18
    plate_h = name_size + gap + sub_size + pad_y * 2

    # black plate keeps the type legible over whatever the venue lighting does
    d.rectangle([x, y_top, x + plate_w, y_top + plate_h], fill=(0, 0, 0, 214))
    # brand rule on the leading edge
    d.rectangle([x, y_top, x + 8, y_top + plate_h], fill=PRIMARY + (255,))

    tx = x + 18 + pad_x
    BT.draw_text(d, (tx, y_top + pad_y - 6), name, name_size, 700, WHITE + (255,))
    BT.draw_text(d, (tx, y_top + pad_y + name_size + gap - 4), line2, sub_size, 500,
                 PRIMARY + (255,))

    img.save(path)
    return plate_w, plate_h


# --------------------------------------------------------------------------- captions

def words_for(clip):
    p = os.path.join(ROOT, "transcripts", clip + ".json")
    with open(p, encoding="utf-8") as f:
        j = json.load(f)
    out = []
    for s in j.get("segments", []):
        for w in s.get("words", []) or []:
            out.append((w["start"], w["end"], w["word"].strip()))
    return out


def cue_split(words):
    """Group words into caption cues, breaking on punctuation, length or a pause."""
    cues, cur = [], []
    for w in words:
        cur.append(w)
        text = " ".join(x[2] for x in cur)
        dur = cur[-1][1] - cur[0][0]
        nxt_gap = 0.0
        ends_sentence = w[2].endswith((".", "?", "!"))
        ends_clause = w[2].endswith((",", ";"))
        if (ends_sentence
                or len(text) >= CAP_MAX_CHARS
                or len(cur) >= CAP_MAX_WORDS
                or dur >= CAP_MAX_SECS
                or (ends_clause and len(text) > 20)):
            cues.append(cur)
            cur = []
    if cur:
        # fold a stray one-word tail into the previous cue
        if cues and len(cur) == 1:
            cues[-1].extend(cur)
        else:
            cues.append(cur)
    return cues


def caption_png(text, path, baseline_bottom):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    size = 52
    max_w = W - 150
    lines = BT.wrap(d, text, size, max_w, 700)
    while len(lines) > 2 and size > 36:
        size -= 3
        lines = BT.wrap(d, text, size, max_w, 700)

    line_h = int(size * 1.22)
    # Plate box comes from the font's real ink bounds, not fixed offsets, so the gap
    # above the ascenders matches the gap below the descenders. With fixed offsets the
    # descenders on g/j/p/q/y overhang the bottom edge -- the flaw found in one build.
    padv = 22 * size / 52
    primary, _ = BT.get_fonts(size, 700)
    ink = primary.getbbox("ABCdfghjklpqty0123456789,'")
    n = len(lines)
    y_last = baseline_bottom - ink[3] - padv        # last plate's bottom edge
    boxes = []
    for i, ln in enumerate(lines):
        y = y_last - (n - 1 - i) * line_h
        tw = BT.text_length(d, ln, size, 700)
        x = (W - tw) / 2
        boxes.append((x - 22, y + ink[1] - padv, x + tw + 22, y + ink[3] + padv, ln, y))

    # rounded pills behind each line for legibility over busy footage; plates first,
    # then text, so an overlapping plate never covers a glyph
    for b in boxes:
        d.rounded_rectangle(b[:4], radius=12, fill=(0, 0, 0, 200))
    for b in boxes:
        tw = BT.text_length(d, b[4], size, 700)
        BT.draw_text(d, ((W - tw) / 2, b[5]), b[4], size, 700, WHITE + (255,))

    img.save(path)


# --------------------------------------------------------------------------- driver

def build():
    with open(os.path.join(ROOT, "bites.json"), encoding="utf-8") as f:
        data = json.load(f)
    with open(os.path.join(ROOT, "speakers.json"), encoding="utf-8") as f:
        speakers = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    manifest = {"lt": {}, "cap": {}}

    for b in data["bites"]:
        bid, clip = b["id"], b["clip"]
        seg_start = max(0.0, b["start"] - HEAD_HANDLE)
        seg_dur = (b["end"] + 0.15) - seg_start

        # ---- lower third
        sp = speakers.get(clip, {})
        if sp.get("name") and seg_dur >= LT_MIN_BITE:
            for variant, y_top in (("lt", 1400), ("ltcap", 1430)):
                p = os.path.join(LT_DIR, "%s_%s.png" % (bid, variant))
                lower_third(sp["name"], sp.get("title"), sp.get("company"), p, y_top)
            manifest["lt"][bid] = {
                "name": sp["name"], "title": sp.get("title"), "company": sp.get("company"),
                "in": 0.35, "out": min(seg_dur - 0.2, 0.35 + LT_DURATION),
            }

        # ---- captions
        words = [w for w in words_for(clip)
                 if w[0] >= seg_start - 0.05 and w[1] <= seg_start + seg_dur + 0.05]
        cues = cue_split(words)
        entries = []
        for n, cue in enumerate(cues):
            text = " ".join(x[2] for x in cue)
            s = max(0.0, cue[0][0] - seg_start - 0.06)
            e = min(seg_dur, cue[-1][1] - seg_start + 0.18)
            # never let a cue run into the next one, or two PNGs stack
            if n + 1 < len(cues):
                e = min(e, cues[n + 1][0][0] - seg_start - 0.04)
            if e - s < 0.35:
                e = min(seg_dur, s + 0.35)
            for variant, bottom in (("cap", 1450), ("ltcap", 1300)):
                p = os.path.join(CAP_DIR, "%s_%02d_%s.png" % (bid, n, variant))
                caption_png(text, p, bottom)
            entries.append({"n": n, "text": text, "start": round(s, 3), "end": round(e, 3)})
        manifest["cap"][bid] = entries
        print("%-4s %s  %2d cues  lt=%s" % (bid, clip, len(entries),
                                            sp.get("name") or "-"))

    with open(os.path.join(ROOT, "overlays.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    BT.report()


if __name__ == "__main__":
    build()
