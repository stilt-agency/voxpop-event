"""Labelled 9:16 sheet of the proposed replacement b-roll, for sign-off."""
import os
import subprocess

from PIL import Image, ImageDraw

import brandtext as BT

import brandkit as BK
ROOT = BK.PROJECT
SRC = BK.SOURCE
BIN = (r"C:\Users\<you>\AppData\Local\Microsoft\WinGet\Packages"
       r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin")
FFMPEG = os.path.join(BIN, "ffmpeg.exe")
OUT = os.path.join(ROOT, "brollsheet")
os.makedirs(OUT, exist_ok=True)

CROP_W = 1215
TW, TH = 270, 480

# clip, time, cx, label, sublabel
SHOTS = [
    ("P1022889", 12.9, 0.50, "John Jester", "keynote montage 1"),
    ("P1022910", 19.7, 0.50, "Rehan Jalil", "keynote montage 2"),
    ("P1022925", 9.8, 0.46, "Beni Sia", "keynote montage 3"),
    ("P1022927", 9.8, 0.50, "Customer panel", "keynote montage 4"),
    ("P1022902", 2.5, 0.50, "Crowd pan A", "front rows, lit"),
    ("P1022890", 4.5, 0.50, "Crowd pan B", "mid rows"),
    ("P1022913", 3.0, 0.50, "Crowd wide", "room scale"),
]

tiles = []
for clip, t, cx, label, sub in SHOTS:
    x = int(max(0, min(3840 - CROP_W, cx * 3840 - CROP_W / 2)))
    f = os.path.join(OUT, "%s_%s.jpg" % (clip, str(t).replace(".", "_")))
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", "%.2f" % t, "-i",
                    os.path.join(SRC, clip + ".MP4"), "-frames:v", "1", "-update", "1",
                    "-vf", "crop=%d:2160:%d:0,scale=%d:%d" % (CROP_W, x, TW, TH), f],
                   capture_output=True)
    im = Image.open(f).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, TH - 72, TW, TH], fill=(0, 0, 0))
    d.rectangle([0, TH - 72, 6, TH], fill=(0, 209, 95))
    BT.draw_text(d, (16, TH - 62), label, 24, 700, (255, 255, 255))
    BT.draw_text(d, (16, TH - 32), sub, 17, 500, (0, 209, 95))
    BT.draw_text(d, (16, TH - 90), "%s @ %.1fs" % (clip, t), 15, 500, (170, 170, 170))
    tiles.append(im)

sheet = Image.new("RGB", (TW * len(tiles), TH), (0, 0, 0))
for i, im in enumerate(tiles):
    sheet.paste(im, (i * TW, 0))
sheet.save(os.path.join(OUT, "BROLL.jpg"), quality=94)
print("wrote BROLL.jpg with %d shots" % len(tiles))
