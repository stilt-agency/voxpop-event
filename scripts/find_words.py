import json, os, sys

import brandkit as BK
ROOT = BK.PROJECT
clip, lo, hi = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
with open(os.path.join(ROOT, "transcripts", clip + ".json"), encoding="utf-8") as f:
    j = json.load(f)
prev_end = None
for s in j["segments"]:
    for w in s.get("words", []) or []:
        if lo <= w["start"] <= hi:
            gap = (w["start"] - prev_end) if prev_end is not None else 0
            print("%8.3f %8.3f  gap %5.2f  %s" % (w["start"], w["end"], gap, w["word"]))
        prev_end = w["end"]
