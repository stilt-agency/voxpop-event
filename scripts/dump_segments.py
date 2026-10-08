import json, glob, os, sys

import brandkit as BK, os
d = os.path.join(BK.PROJECT, "transcripts")
want = sys.argv[1:] if len(sys.argv) > 1 else None

for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    base = os.path.splitext(os.path.basename(f))[0]
    if want and base not in want:
        continue
    with open(f, "r", encoding="utf-8") as fh:
        j = json.load(fh)
    segs = j.get("segments", [])
    if not segs:
        continue
    print("=== %s ===" % base)
    for s in segs:
        print("%8.2f %8.2f  %s" % (s["start"], s["end"], s["text"].strip()))
    print()
