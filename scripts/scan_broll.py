"""Contact-sheet a set of (clip, time) candidates so b-roll picks can be eyeballed."""
import os
import subprocess
import sys

BIN = (r"C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages"
       r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin")
FFMPEG = os.path.join(BIN, "ffmpeg.exe")
import brandkit as BK
SRC = BK.SOURCE
OUT = os.path.join(BK.PROJECT, "brollpick")
os.makedirs(OUT, exist_ok=True)

# label -> (clip, time). Rendered as the 9:16 centre crop so what you see is
# what the cut would actually use.
CANDS = [
    ("jester-a", "P1022887", 2.0),
    ("jester-b", "P1022896", 3.0),
    ("jester-c", "P1022900", 10.0),
    ("jester-d", "P1022904", 2.0),
    ("rehan-a", "P1022909", 6.0),
    ("rehan-b", "P1022912", 12.0),
    ("rehan-c", "P1022913", 14.0),
    ("rehan-d", "P1022921", 4.0),
    ("beni-a", "P1022925", 4.0),
    ("beni-b", "P1022925", 10.0),
    ("panel-a", "P1022926", 8.0),
    ("panel-b", "P1022927", 10.0),
    ("crowd-a", "P1022888", 8.0),
    ("crowd-b", "P1022889", 12.0),
    ("crowd-c", "P1022890", 4.0),
    ("crowd-d", "P1022897", 5.0),
    ("crowd-e", "P1022899", 5.0),
    ("crowd-f", "P1022902", 3.0),
    ("crowd-g", "P1022910", 20.0),
    ("crowd-h", "P1022911", 8.0),
    ("stage-a", "P1022892", 3.0),
    ("stage-b", "P1022930", 4.0),
    ("stage-c", "P1022929", 5.0),
    ("stage-d", "P1022928", 7.0),
]

if len(sys.argv) > 1:
    CANDS = []
    a = sys.argv[1:]
    for i in range(0, len(a), 3):
        CANDS.append((a[i], a[i + 1], float(a[i + 2])))

CROP_W = 1215
x = (3840 - CROP_W) // 2

frames = []
for label, clip, t in CANDS:
    f = os.path.join(OUT, "%s.jpg" % label)
    p = subprocess.run(
        [FFMPEG, "-v", "error", "-y", "-ss", "%.2f" % t, "-i",
         os.path.join(SRC, clip + ".MP4"), "-frames:v", "1", "-update", "1",
         "-vf", "crop=%d:2160:%d:0,scale=200:356" % (CROP_W, x), f],
        capture_output=True, text=True)
    if p.returncode == 0:
        frames.append((label, f))
    else:
        print("FAIL", label, p.stderr[-200:])

lst = os.path.join(OUT, "_l.txt")
with open(lst, "w", encoding="ascii") as fh:
    for _, f in frames:
        fh.write("file '%s'\n" % f.replace(chr(92), "/"))
cols = 8
rows = (len(frames) + cols - 1) // cols
subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                "-vf", "tile=%dx%d:color=black" % (cols, rows), "-frames:v", "1",
                os.path.join(OUT, "SHEET.jpg")])
print("%d frames" % len(frames))
for i, (label, _) in enumerate(frames):
    print("%2d %-10s %s" % (i + 1, label, CANDS[i][1]))
