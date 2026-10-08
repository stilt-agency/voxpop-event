"""Report the words either side of every chosen in/out point."""
import json, os

import brandkit as BK
ROOT = BK.PROJECT

with open(os.path.join(ROOT, "bites.json"), encoding="utf-8") as f:
    data = json.load(f)


def words_for(clip):
    p = os.path.join(ROOT, "transcripts", clip + ".json")
    with open(p, encoding="utf-8") as f:
        j = json.load(f)
    out = []
    for s in j.get("segments", []):
        for w in s.get("words", []) or []:
            out.append((w["start"], w["end"], w["word"]))
    return out


for b in data["bites"]:
    ws = words_for(b["clip"])
    if not ws:
        print(b["id"], b["clip"], "NO WORD TIMINGS")
        continue
    s, e = b["start"], b["end"]

    before = [w for w in ws if w[1] <= s][-4:]
    inside = [w for w in ws if w[0] >= s and w[1] <= e]
    after = [w for w in ws if w[0] >= e][:4]
    straddle_in = [w for w in ws if w[0] < s < w[1]]
    straddle_out = [w for w in ws if w[0] < e < w[1]]

    head_gap = (inside[0][0] - s) if inside else 0
    tail_gap = (e - inside[-1][1]) if inside else 0

    flag = ""
    if straddle_in:
        flag += "  !! IN cuts word '%s'" % straddle_in[0][2].strip()
    if straddle_out:
        flag += "  !! OUT cuts word '%s'" % straddle_out[0][2].strip()
    if head_gap < 0.10:
        flag += "  ! tight head %.2fs" % head_gap
    if tail_gap < 0.10:
        flag += "  ! tight tail %.2fs" % tail_gap

    print("%s %s  %.2f-%.2f%s" % (b["id"], b["clip"], s, e, flag))
    print("     before: ...%s" % "".join(w[2] for w in before))
    print("     starts:%s" % "".join(w[2] for w in inside[:9]))
    print("     ends:  ...%s" % "".join(w[2] for w in inside[-9:]))
    print("     after: %s..." % "".join(w[2] for w in after))
    print()
