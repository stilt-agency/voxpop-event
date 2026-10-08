"""
Cross-checked transcripts for every interview clip.

Three reads per clip (Whisper large-v2, Whisper large-v3, and one independent
source, normally Descript), merged by the anchor-and-vote method. The merged
result is written in Whisper's own shape, so every downstream script
(dump_segments, make_overlays, build) reads it without knowing the difference.

  python transcripts_build.py asr            # the two Whisper passes
  python transcripts_build.py prep           # mono mp3s to upload to Descript
  python transcripts_build.py merge          # vote, write transcripts/*.json
  python transcripts_build.py status         # what is still missing

Between `prep` and `merge`: upload work/descript_upload/*.mp3 to Descript,
export each as txt with paragraph timecodes, and save them as
asr/descript/<clip>.txt. See reference/captions.md.
"""
import json
import os
import subprocess
import sys

import brandkit as BK
import transcripts_merge as TM

ROOT = BK.PROJECT
CLIPS = BK.cfg("footage.source_dirs")
ASR = os.path.join(ROOT, "asr")
PREP = os.path.join(ROOT, "work", "descript_upload")
OUT = os.path.join(ROOT, "transcripts")
MERGED = os.path.join(ROOT, "merged")


def clips():
    """Interview clips: everything listed in bites.json, else every video."""
    bites = os.path.join(ROOT, "bites.json")
    if os.path.exists(bites):
        d = json.load(open(bites, encoding="utf-8"))
        return sorted({b["clip"] for b in d.get("bites", [])})
    out = []
    for d in CLIPS:
        for f in sorted(os.listdir(d)):
            if f.lower().endswith((".mp4", ".mov", ".mxf", ".braw")):
                out.append(os.path.splitext(f)[0])
    return out


def source(stem):
    for d in CLIPS:
        for ext in (".MP4", ".mp4", ".MOV", ".mov", ".mxf"):
            p = os.path.join(d, stem + ext)
            if os.path.exists(p):
                return p
    raise SystemExit("no source for " + stem)


def wavs():
    w = os.path.join(ROOT, "work", "audio")
    os.makedirs(w, exist_ok=True)
    out = []
    for stem in clips():
        p = os.path.join(w, stem + ".wav")
        if not os.path.exists(p):
            subprocess.run([BK.FFMPEG, "-v", "error", "-y", "-i", source(stem),
                            "-ac", "1", "-ar", "16000", p], check=True)
        out.append(p)
    return out


def asr():
    for model, sub in (("large-v2", "v2"), ("large-v3", "v3")):
        d = os.path.join(ASR, sub)
        os.makedirs(d, exist_ok=True)
        todo = [w for w in wavs()
                if not os.path.exists(os.path.join(d, os.path.basename(w)[:-4] + ".json"))]
        if not todo:
            continue
        print("%s: %d clips" % (model, len(todo)))
        subprocess.run([BK.WHISPER] + todo + ["--model", model, "-wt", "True",
                       "--output_format", "json", "--output_dir", d,
                       "--device", "cuda", "--compute_type", "float16",
                       "--language", "en"], check=False)


def prep():
    """Small mono mp3s for the third source. Keep the clip stem as the name:
    the merge matches on it."""
    os.makedirs(PREP, exist_ok=True)
    for stem in clips():
        p = os.path.join(PREP, stem + ".mp3")
        if not os.path.exists(p):
            subprocess.run([BK.FFMPEG, "-v", "error", "-y", "-i", source(stem),
                            "-ac", "1", "-b:a", "96k", p], check=True)
    print("upload to the third source: %s" % PREP)
    print("save each export as asr/descript/<clip>.txt (txt, paragraph timecodes)")


def status():
    rows = []
    for stem in clips():
        have = [s for s in ("v2", "v3", "descript")
                if os.path.exists(os.path.join(ASR, s, stem + (".txt" if s == "descript" else ".json")))]
        rows.append((stem, have))
    for stem, have in rows:
        missing = [s for s in ("v2", "v3", "descript") if s not in have]
        print("%-16s %s" % (stem, "complete" if not missing else "missing " + ", ".join(missing)))
    return rows


def merge():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MERGED, exist_ok=True)
    flagged = []
    for stem, have in status():
        if len(have) < 3:
            continue
        words, review = TM.merge(stem,
                                 os.path.join(ASR, "v2", stem + ".json"),
                                 os.path.join(ASR, "v3", stem + ".json"),
                                 os.path.join(ASR, "descript", stem + ".txt"),
                                 MERGED)
        # Whisper's shape, so the rest of the pipeline is unchanged
        segs, cur = [], []
        for w in words:
            if cur and (w["start"] - cur[-1]["end"] > 0.8 or len(cur) >= 14):
                segs.append(cur)
                cur = []
            cur.append(w)
        if cur:
            segs.append(cur)
        json.dump({"segments": [
            {"start": s[0]["start"], "end": s[-1]["end"],
             "text": " ".join(x["text"] for x in s),
             "words": [{"start": x["start"], "end": x["end"], "word": " " + x["text"],
                        "probability": 1.0} for x in s]}
            for s in segs]}, open(os.path.join(OUT, stem + ".json"), "w", encoding="utf-8"),
            indent=0, ensure_ascii=False)
        flagged += [(stem,) + tuple(r) for r in review if r[1] == "no majority"]
    if flagged:
        print("\nREAD THESE BEFORE CAPTIONS. No majority among the three reads:")
        for f in flagged:
            print("   %-16s %s  v2=%r v3=%r third=%r" % (f[0], TM.ts(f[1]) if hasattr(TM, "ts") else f[1],
                                                         f[3], f[4], f[5]))
    print("\n%d clips merged -> %s" % (len(os.listdir(OUT)), OUT))


if __name__ == "__main__":
    {"asr": asr, "prep": prep, "merge": merge, "status": status}[sys.argv[1]]()
