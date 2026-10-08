"""
Build the vox pop set, 1080x1920.

Pipeline
  1. Render every distinct element once into segs/ (cards, b-roll, speech bites,
     opener, producer outro). Elements shared between programmes are decoded
     from the 4K source only once.
  2. Burn the three overlay treatments (lower thirds, captions, both) onto the
     finished 1080x1920 speech segments. Working from the cropped segment rather
     than the source keeps framing identical across treatments and is cheap.
  3. Concat each programme x each treatment, then loop the music bed to length,
     sidechain-duck it against the speech, and mix.

Speech levelling is a flat per-clip gain, not dynamic normalisation, so
delivery stays natural.
"""

import json
import os
import re
import shutil
import subprocess
import sys

import brandkit as BK
import programmes as P

ROOT = BK.PROJECT
SRC = BK.SOURCE
FFMPEG = BK.FFMPEG
FFPROBE = BK.FFPROBE
OUTRO_SRC = BK.OUTRO
# the client's own animated slate, from their brand media kit
BRAND_BG = BK.BACKDROP

W, H = 1080, 1920
FPS = int(BK.BRAND.get("fps", 25))          # match the source, do not resample
CROP_W = int(BK.BRAND.get("crop_w", 1215))  # 9:16 slice of a 3840x2160 frame
TARGET_LUFS = -16.0
MUSIC = BK.MUSIC

# 1920x1080 up to 9:16. A backdrop is normally an abstract soft gradient with no
# fine detail, so the upscale costs nothing visible. Check yours.
BG_VF = ("scale=3413:1920:flags=lanczos,crop=%d:%d:(iw-%d)/2:0,setsar=1,fps=%d"
         % (W, H, W, FPS))

# Different offsets into the backdrop so repeated slates do not match.
BG_OFFSET = {k: v for k, v in BK.BG_OFFSET.items() if not k.startswith("_note")}

SEGS = os.path.join(ROOT, "segs")
OUTDIR = os.path.join(ROOT, "out")
os.makedirs(SEGS, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

VENC = ["-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS * 2), "-movflags", "+faststart"]
AENC = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]

# Whisper snaps word times to segment edges, so cuts land exactly on speech
# onset. Handles give the delivery room; the edge fades kill joins clicks.
HEAD_HANDLE = 0.12
TAIL_HANDLE = 0.15
EDGE_FADE = 0.05
LT_FADE = 0.28

TREATMENTS = {"plain": "", "lt": "-LOWERTHIRDS", "cap": "-CAPTIONS",
              "ltcap": "-LOWERTHIRDS-CAPTIONS"}

# Overlay burns. A speech bite is rendered in each of these once, then each
# programme picks per bite which burn to use.
#   name       -> (draw lower third, caption position key or None)
# "caphigh" is captions at the with-lower-third height but no plate. It exists
# so that in the LOWERTHIRDS-CAPTIONS treatment the caption line stays at one
# height for the whole video, including on the shots that carry no plate.
BURNS = {
    "lt": (True, None),
    "cap": (False, "cap"),
    "ltcap": (True, "ltcap"),
    "caphigh": (False, "ltcap"),
}


def run(args):
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(" ".join(str(a) for a in args)[:2000] + "\n")
        sys.stderr.write(p.stderr[-3000:] + "\n")
        raise SystemExit("ffmpeg failed")
    return p


def duration(path):
    p = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(p.stdout.strip())


def measure_lufs(path, start=None, dur=None):
    args = [FFMPEG, "-hide_banner", "-nostats"]
    if start is not None:
        args += ["-ss", "%.3f" % start]
    args += ["-i", path]
    if dur is not None:
        args += ["-t", "%.3f" % dur]
    args += ["-map", "0:a:0", "-af", "ebur128=framelog=quiet", "-f", "null", "-"]
    p = subprocess.run(args, capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+)\s+LUFS", p.stderr)
    return float(m[-1]) if m else None


def crop_x(cx):
    return int(max(0, min(3840 - CROP_W, cx * 3840 - CROP_W / 2)))


# --------------------------------------------------------------------- elements

def seg_name(el):
    kind = el[0]
    if kind == "opener":
        return "e_opener.mp4"
    if kind == "outro":
        return "e_outro.mp4"
    if kind == "card":
        return "e_card_%s_%s.mp4" % (el[1], str(el[2]).replace(".", "_"))
    return "e_%s_%s.mp4" % (kind, el[1])


def render_card(stem, dur, out):
    """Question cards are flat brand-colour stills. The title and end slates are
    transparent artwork composited over the client's animated background."""
    flat = os.path.join(ROOT, "cards", stem + ".jpg")
    fo = max(0.0, dur - 0.22)
    fades = "fade=t=in:st=0:d=0.18,fade=t=out:st=%.2f:d=0.22" % fo

    if os.path.exists(flat):
        run([FFMPEG, "-v", "error", "-y", "-loop", "1", "-i", flat,
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-t", "%.3f" % dur, "-map", "0:v:0", "-map", "1:a:0",
             "-vf", "scale=%d:%d,setsar=1,%s" % (W, H, fades)] + VENC + AENC + [out])
        return

    art = os.path.join(ROOT, "cards", stem + ".png")
    off = BG_OFFSET.get(stem, 0.0)
    fc = ("[0:v]%s,trim=0:%.3f,setpts=PTS-STARTPTS[bg];"
          "[1:v]setpts=PTS-STARTPTS[art];"
          "[bg][art]overlay=0:0:shortest=1,%s[v]" % (BG_VF, dur, fades))
    run([FFMPEG, "-v", "error", "-y", "-ss", "%.2f" % off, "-i", BRAND_BG,
         "-loop", "1", "-t", "%.3f" % dur, "-i", art,
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-filter_complex", fc, "-t", "%.3f" % dur,
         "-map", "[v]", "-map", "2:a:0"] + VENC + AENC + [out])


def render_opener(out):
    """The client's animated background with their vector logo scaling and
    fading up over it."""
    dur = len(os.listdir(os.path.join(ROOT, "opener"))) / FPS
    fc = ("[0:v]%s,trim=0:%.3f,setpts=PTS-STARTPTS[bg];"
          "[1:v]setpts=PTS-STARTPTS[lg];"
          "[bg][lg]overlay=0:0:shortest=1[v]" % (BG_VF, dur))
    run([FFMPEG, "-v", "error", "-y", "-ss", "%.2f" % BG_OFFSET["_opener"], "-i", BRAND_BG,
         "-framerate", str(FPS), "-i", os.path.join(ROOT, "opener", "f%04d.png"),
         "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
         "-filter_complex", fc, "-t", "%.3f" % dur,
         "-map", "[v]", "-map", "2:a:0"] + VENC + AENC + [out])


def render_outro(out):
    """The producer's logo reveal, letterboxed into 9:16.

    A 16:9 reveal with a tagline is wider than a 9:16 crop can hold, so scale to
    fit and pad rather than cropping the tagline off. If the source blacks are a
    textured grid rather than true black, crush them or the padded area reads as
    a lighter band. Check yours and adjust the lutyuv threshold.
    """
    vf = ("scale=2190:1232,crop=%d:1232:555:0,format=yuv420p,"
          "lutyuv=y='if(lt(val,48),16,val)',"
          "pad=%d:%d:0:344:color=black,setsar=1,fps=%d" % (W, W, H, FPS))
    lufs = measure_lufs(OUTRO_SRC)
    gain = max(-12.0, min(12.0, -17.0 - lufs))
    af = "volume=%.2fdB,afade=t=out:st=4.6:d=0.6,aresample=48000" % gain
    run([FFMPEG, "-v", "error", "-y", "-i", OUTRO_SRC,
         "-map", "0:v:0", "-map", "0:a:0", "-vf", vf, "-af", af] + VENC + AENC + [out])


def render_clip(bid, bites, crops, mute, out):
    b = bites[bid]
    start = max(0.0, b["start"] - (0.0 if mute else HEAD_HANDLE))
    end = b["end"] + (0.0 if mute else TAIL_HANDLE)
    dur = end - start
    src = os.path.join(SRC, b["clip"] + ".MP4")
    x = crop_x(crops[bid])
    vf = "crop=%d:2160:%d:0,scale=%d:%d:flags=lanczos,setsar=1" % (CROP_W, x, W, H)

    if mute:
        run([FFMPEG, "-v", "error", "-y", "-ss", "%.3f" % start, "-i", src,
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-t", "%.3f" % dur, "-map", "0:v:0", "-map", "1:a:0",
             "-vf", vf] + VENC + AENC + [out])
        return

    lufs = measure_lufs(src, start, dur)
    gain = max(-12.0, min(18.0, TARGET_LUFS - (lufs if lufs else TARGET_LUFS)))
    af = ("highpass=f=80,volume=%.2fdB,"
          "afade=t=in:st=0:d=%.3f,afade=t=out:st=%.3f:d=%.3f,"
          "alimiter=limit=0.89:level=disabled,aresample=48000"
          % (gain, EDGE_FADE, dur - EDGE_FADE, EDGE_FADE))
    print("   %-4s %s %6.2fs  in %6.1f LUFS  gain %+5.1f dB"
          % (bid, b["clip"], dur, lufs or 0, gain))
    run([FFMPEG, "-v", "error", "-y", "-ss", "%.3f" % start, "-i", src,
         "-t", "%.3f" % dur, "-map", "0:v:0", "-map", "0:a:0",
         "-vf", vf, "-af", af] + VENC + AENC + [out])


# --------------------------------------------------------------------- overlays

def render_variant(seg_file, bid, burn, overlays):
    want_lt, cap_key = BURNS[burn]
    src = os.path.join(SEGS, seg_file)
    vdir = os.path.join(SEGS, burn)
    os.makedirs(vdir, exist_ok=True)
    out = os.path.join(vdir, seg_file)

    lt = overlays["lt"].get(bid) if want_lt else None
    cues = overlays["cap"].get(bid, []) if cap_key else []
    if not lt and not cues:
        shutil.copyfile(src, out)
        return

    dur = duration(src)
    args = [FFMPEG, "-v", "error", "-y", "-i", src]
    parts, idx, chain = [], 1, "[0:v]"

    if lt:
        # the plate sits lower when captions share the frame
        lt_pos = "ltcap" if cap_key == "ltcap" else "lt"
        args += ["-loop", "1", "-t", "%.3f" % dur, "-i",
                 os.path.join(ROOT, "ov_lt", "%s_%s.png" % (bid, lt_pos))]
        fo = max(lt["in"], lt["out"] - LT_FADE)
        parts.append("[%d:v]format=rgba,fade=t=in:st=%.3f:d=%.2f:alpha=1,"
                     "fade=t=out:st=%.3f:d=%.2f:alpha=1[lt]"
                     % (idx, lt["in"], LT_FADE, fo, LT_FADE))
        parts.append("%s[lt]overlay=0:0:enable='between(t,%.3f,%.3f)'[v%d]"
                     % (chain, lt["in"], lt["out"], idx))
        chain = "[v%d]" % idx
        idx += 1

    for c in cues:
        args += ["-loop", "1", "-t", "%.3f" % dur, "-i",
                 os.path.join(ROOT, "ov_cap", "%s_%02d_%s.png" % (bid, c["n"], cap_key))]
        parts.append("%s[%d:v]overlay=0:0:enable='between(t,%.3f,%.3f)'[v%d]"
                     % (chain, idx, c["start"], c["end"], idx))
        chain = "[v%d]" % idx
        idx += 1

    args += ["-filter_complex", ";".join(parts), "-map", chain, "-map", "0:a:0"]
    run(args + VENC + AENC + [out])


# --------------------------------------------------------------------- assembly

def badged_bites(elements, bites, overlays):
    """One name plate per person per video, on their first eligible appearance.

    A bite is eligible if a lower third was generated for it, which excludes
    shots under five seconds and anyone whose badge was never legible. If a
    person's first appearance is not eligible, the next one carries the plate
    instead.
    """
    seen, chosen = set(), set()
    for el in elements:
        if el[0] != "bite":
            continue
        bid = el[1]
        clip = bites[bid]["clip"]
        if clip in seen or bid not in overlays["lt"]:
            continue
        seen.add(clip)
        chosen.add(bid)
    return chosen


def concat_and_mix(elements, out_path, label, treatment, bites, overlays):
    badged = badged_bites(elements, bites, overlays) if treatment in ("lt", "ltcap") else set()

    def source_dir(el):
        if treatment == "plain":
            return SEGS
        if el[0] != "bite":
            # cards, b-roll, opener and outro never carry overlays
            return SEGS
        if treatment == "cap":
            return os.path.join(SEGS, "cap")
        if treatment == "lt":
            return os.path.join(SEGS, "lt") if el[1] in badged else SEGS
        # ltcap: plate only on the first appearance, captions stay at one height
        return os.path.join(SEGS, "ltcap" if el[1] in badged else "caphigh")

    lst = os.path.join(SEGS, "_c_%s.txt" % label)
    with open(lst, "w", encoding="ascii") as f:
        for el in elements:
            f.write("file '%s'\n"
                    % os.path.join(source_dir(el), seg_name(el)).replace("\\", "/"))

    silent = os.path.join(SEGS, "_j_%s.mp4" % label)
    run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", silent])
    total = duration(silent)

    mus_gain = max(-30.0, min(6.0, -19.0 - measure_lufs(MUSIC)))
    fc = (
        "[1:a]aloop=loop=-1:size=2e9,atrim=0:%(t).3f,"
        "volume=%(g).2fdB,afade=t=in:st=0:d=1.2,afade=t=out:st=%(fo).3f:d=2.0[mus];"
        "[0:a]aformat=channel_layouts=stereo,asplit=2[sp][key];"
        "[mus][key]sidechaincompress=threshold=0.012:ratio=16:attack=12:release=420:"
        "makeup=1[duck];"
        "[sp][duck]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        "alimiter=limit=0.89:level=disabled,aresample=48000[a]"
        % {"t": total, "g": mus_gain, "fo": max(0.0, total - 2.0)}
    )
    run([FFMPEG, "-v", "error", "-y", "-i", silent, "-i", MUSIC,
         "-filter_complex", fc, "-map", "0:v:0", "-map", "[a]",
         "-c:v", "copy"] + AENC + ["-movflags", "+faststart", out_path])
    os.remove(silent)
    return total


def main():
    with open(os.path.join(ROOT, "bites.json"), encoding="utf-8") as f:
        data = json.load(f)
    bites = {b["id"]: b for b in data["bites"] + data["broll"]}
    with open(os.path.join(ROOT, "crops.json"), encoding="utf-8") as f:
        crops = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    with open(os.path.join(ROOT, "overlays.json"), encoding="utf-8") as f:
        overlays = json.load(f)
    with open(os.path.join(ROOT, "speakers.json"), encoding="utf-8") as f:
        speakers = {k: v for k, v in json.load(f).items() if not k.startswith("_")}

    progs = P.all_programmes()

    # unique elements across every programme
    elements, speech = {}, set()
    for els in progs.values():
        for el in els:
            elements[seg_name(el)] = el
            if el[0] == "bite":
                speech.add(el[1])

    print("Rendering %d unique elements..." % len(elements))
    for name, el in sorted(elements.items()):
        out = os.path.join(SEGS, name)
        if os.path.exists(out) and "--reuse" in sys.argv:
            continue
        kind = el[0]
        if kind == "opener":
            render_opener(out)
        elif kind == "outro":
            render_outro(out)
        elif kind == "card":
            render_card(el[1], el[2], out)
        elif kind == "bite":
            render_clip(el[1], bites, crops, False, out)
        elif kind == "broll":
            render_clip(el[1], bites, crops, True, out)

    print("Burning %d overlay states across %d speech segments..."
          % (len(BURNS), len(speech)))
    for burn in BURNS:
        for bid in sorted(speech):
            render_variant("e_bite_%s.mp4" % bid, bid, burn, overlays)

    print("Assembling %d programmes x %d treatments..." % (len(progs), len(TREATMENTS)))
    rows = []
    for pname in sorted(progs):
        badged = badged_bites(progs[pname], bites, overlays)
        names = [speakers[bites[el[1]]["clip"]]["name"]
                 for el in progs[pname] if el[0] == "bite" and el[1] in badged]
        for treatment, suffix in TREATMENTS.items():
            fname = BK.out_name(pname, suffix)
            t = concat_and_mix(progs[pname], os.path.join(OUTDIR, fname),
                               "%s_%s" % (pname, treatment), treatment, bites, overlays)
            if treatment == "plain":
                rows.append((pname, t, len(badged), names))
    print()
    for pname, t, n, names in rows:
        print("  %-24s %5.1fs (%d:%02d)  %d plate%s: %s"
              % (pname, t, int(t) // 60, int(t) % 60, n, "" if n == 1 else "s",
                 ", ".join(names)))
    print("\n%d files written to %s" % (len(progs) * len(TREATMENTS), OUTDIR))


if __name__ == "__main__":
    main()
