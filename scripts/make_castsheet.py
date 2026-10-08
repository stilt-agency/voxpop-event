"""Labelled 9:16 contact sheet of candidate interviewees, for sign-off."""
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
OUT = os.path.join(ROOT, "cast")
os.makedirs(OUT, exist_ok=True)

CROP_W = 1215
TW, TH = 300, 533

# clip, time, cx, name, company
CAST = [
    ("P1022934", 30.0, 0.40, "William Kusa", "Willyama Services"),
    ("P1022935", 40.0, 0.40, "Darren Elsby", "Ingram Micro"),
    ("P1022939", 20.0, 0.62, "Andrew Panting", "A23"),
    # EXAMPLE ROWS from a past job. Replace with your own:
    #   (clip stem, seconds into clip, horizontal crop centre 0-1, name, company)
    ("P1022940", 30.0, 0.62, "Jordan Xu", "Example Corp"),
    ("P1022943", 45.0, 0.66, "Anthony Spencer", "The Missing Link"),
    ("P1022947", 15.0, 0.42, "Behzaad Habibi", "Example Corp"),
]

tiles = []
for clip, t, cx, name, company in CAST:
    x = int(max(0, min(3840 - CROP_W, cx * 3840 - CROP_W / 2)))
    f = os.path.join(OUT, "%s.jpg" % clip)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", "%.2f" % t, "-i",
                    os.path.join(SRC, clip + ".MP4"), "-frames:v", "1", "-update", "1",
                    "-vf", "crop=%d:2160:%d:0,scale=%d:%d" % (CROP_W, x, TW, TH), f],
                   capture_output=True)
    im = Image.open(f).convert("RGB")
    d = ImageDraw.Draw(im)
    d.rectangle([0, TH - 78, TW, TH], fill=(0, 0, 0))
    d.rectangle([0, TH - 78, 6, TH], fill=(0, 209, 95))
    BT.draw_text(d, (18, TH - 68), name, 26, 700, (255, 255, 255))
    BT.draw_text(d, (18, TH - 36), company, 19, 500, (0, 209, 95))
    BT.draw_text(d, (18, TH - 96), clip, 16, 500, (170, 170, 170))
    tiles.append(im)

sheet = Image.new("RGB", (TW * 6, TH), (0, 0, 0))
for i, im in enumerate(tiles):
    sheet.paste(im, (i * TW, 0))
sheet.save(os.path.join(OUT, "CAST.jpg"), quality=94)
print("wrote CAST.jpg with %d candidates" % len(tiles))
