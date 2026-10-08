"""
Every client-specific value in one place.

The pipeline is the same job each time; only the branding moves. So no script
below this one hardcodes a colour, a typeface, a logo or an asset path. They
import this and read from `brand.json`, which sits in the project folder.

Find the project by walking up from wherever the script runs, so the scripts
can live in the skill folder and the project can live anywhere.
"""

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


CONFIG_NAMES = ("project.json", "brand.json")   # project.json is the intake's


def _find_project(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        for name in CONFIG_NAMES:
            if os.path.exists(os.path.join(d, name)):
                return d, name
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit(
                "No project.json found. Run the intake (reference/intake.md), or "
                "copy project.example.json from the skill's scripts folder into "
                "your project root, fill it in, and run from inside the project."
            )
        d = parent


PROJECT, CONFIG_NAME = _find_project()
# utf-8-sig, because Windows editors and PowerShell routinely write a BOM and
# the plain utf-8 reader rejects it outright
with open(os.path.join(PROJECT, CONFIG_NAME), encoding="utf-8-sig") as _f:
    BRAND = json.load(_f)


def cfg(path, default=None):
    """Dotted lookup into the config: cfg("output.dir"), cfg("captions.fixes", []).

    Paths under a key ending in dir/dirs/path/file are returned absolute."""
    node = BRAND
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    leaf = path.rsplit(".", 1)[-1]
    if leaf.endswith(("dir", "path", "file")) and isinstance(node, str):
        return _abs(node)
    if leaf.endswith(("dirs", "paths", "files")) and isinstance(node, list):
        return [_abs(p) for p in node]
    return node


def _abs(p):
    """Relative paths resolve against the project; absolute ones pass through."""
    if not p:
        return None
    return p if os.path.isabs(p) else os.path.join(PROJECT, p)


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ------------------------------------------------------------------ identity
CLIENT = BRAND.get("client", "Client")
EVENT = BRAND.get("event", "")

# ------------------------------------------------------------------ colour
_c = BRAND.get("colours", {})
PRIMARY = rgb(_c.get("primary", "#00D15F"))
BLACK = rgb(_c.get("black", "#000000"))
WHITE = rgb(_c.get("white", "#FFFFFF"))
MUTED = rgb(_c.get("muted", "#CDCDCD"))

# ------------------------------------------------------------------ type
_f = BRAND.get("fonts", {})
FONT_DIR = _abs(_f.get("dir", "assets/fonts"))
# weight -> filename, e.g. {"400": "Foo-Regular.ttf", "700": "Foo-Bold.ttf"}
FONT_WEIGHTS = {int(k): v for k, v in _f.get("weights", {}).items()}
FONT_FALLBACK = _abs(_f.get("fallback")) or os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts",
    "Figtree-VariableFont_wght.ttf")

# ------------------------------------------------------------------ logo
_l = BRAND.get("logo", {})
LOGO_MAIN = _abs(_l.get("main"))          # positive, for light/black grounds
LOGO_REVERSE = _abs(_l.get("reverse"))    # white/outline, for the brand colour
LOGO_CLEAR_RATIO = _l.get("clear_space_ratio", 0.55)

# Optional secondary graphic device (a brand mark used large and faded)
_d = BRAND.get("device", {})
DEVICE = _abs(_d.get("path"))
DEVICE_OPACITY = _d.get("opacity", 0.13)

# ------------------------------------------------------------------ footage
_a = BRAND.get("assets", {})
BACKDROP = _abs(_a.get("backdrop"))       # client-supplied animated background
OUTRO = _abs(_a.get("outro"))             # producer logo reveal, e.g. your own
MUSIC = _abs(_a.get("music"))
SOURCE = _abs(_a.get("source_footage", "."))

# Where to sample the backdrop for each still, so repeated cards do not show
# the same frames. Keys are card stems.
BG_OFFSET = BRAND.get("backdrop_offsets", {})

# ------------------------------------------------------------------ copy
COPY = BRAND.get("copy", {})
QUESTIONS = BRAND.get("questions", [])

# ------------------------------------------------------------------ tooling
_t = BRAND.get("tools", {})
FFMPEG = _t.get("ffmpeg") or "ffmpeg"
FFPROBE = _t.get("ffprobe") or "ffprobe"
WHISPER = _t.get("whisper")


# ------------------------------------------------------------------ delivery
OUT_DIR = _abs(BRAND.get("output", {}).get("dir", "out"))
RATIOS = BRAND.get("output", {}).get("ratios", ["9x16"])
TREATMENTS = BRAND.get("output", {}).get("treatments", ["plain", "lt", "cap", "ltcap"])
VERSION_PREFIX = BRAND.get("output", {}).get("version_prefix") or ""

# ------------------------------------------------------------------ watermark
_w = BRAND.get("watermark", {})
WATERMARK = _abs(_w.get("path"))
WATERMARK_CORNER = _w.get("corner", "top-right")
WATERMARK_WIDTH = _w.get("width_px", 190)
WATERMARK_MARGIN = _w.get("margin_px", 48)
WATERMARK_OPACITY = _w.get("opacity", 0.85)

# ------------------------------------------------------------------ captions
CAPTIONS = BRAND.get("captions", {})
CAPTION_FIXES = [tuple(f) for f in CAPTIONS.get("fixes", [])]
SPELLING = CAPTIONS.get("spelling", "en-AU")

TARGET_LUFS = BRAND.get("audio", {}).get("target_lufs", -16.0)


def out_name(programme, treatment_suffix, ratio="9x16", ext="mp4"):
    """From output.name_pattern, or the house default. No spaces."""
    slug = "-".join(x for x in (CLIENT, EVENT) if x).replace(" ", "-")
    pattern = BRAND.get("output", {}).get("name_pattern")
    if pattern:
        name = pattern.format(client=CLIENT.replace(" ", "-"), event=EVENT.replace(" ", "-"),
                              event_slug=slug, programme=programme, ratio=ratio,
                              treatments=treatment_suffix, ext=ext)
    else:
        name = "%s-VoxPop-%s-%s%s.%s" % (slug, ratio, programme, treatment_suffix, ext)
    return VERSION_PREFIX + name


def report():
    print("project: %s / %s   (%s)" % (CLIENT, EVENT or "no event", CONFIG_NAME))
    print("  folder   %s" % PROJECT)
    print("  output   %s" % OUT_DIR)
    print("  deliver  %s x %s" % (", ".join(RATIOS), ", ".join(TREATMENTS)))
    for label, p in (("backdrop", BACKDROP), ("outro", OUTRO), ("music", MUSIC),
                     ("logo", LOGO_MAIN), ("logo rev", LOGO_REVERSE),
                     ("watermark", WATERMARK)):
        if p is None:
            print("  %-9s not set" % label)
        elif os.path.exists(p):
            print("  %-9s ok       %s" % (label, p))
        else:
            print("  %-9s MISSING  %s" % (label, p))
    for d in cfg("footage.source_dirs", []) or []:
        print("  %-9s %s  %s" % ("footage", "ok     " if os.path.isdir(d) else "MISSING", d))
    third = CAPTIONS.get("third_source")
    print("  captions %s, third read: %s" % (", ".join(CAPTIONS.get("deliver", ["burned"])),
                                             third or "NOT SET (see reference/captions.md)"))
    for item in BRAND.get("open_items", []):
        print("  OPEN     %s (%s) blocks %s" % (item.get("item"), item.get("owner"),
                                                item.get("blocks")))


if __name__ == "__main__":
    report()
