"""Merge three independent transcripts of one isolated speech track.

  v3        Faster-Whisper large-v3 JSON (word timings)
  v2        Faster-Whisper large-v2 JSON (word timings)
  descript  Descript export, txt with [hh:mm:ss] paragraph timecodes

Method: anchor, then vote per window.
  1. Anchors are words all three engines agree on, in order.
  2. Between two anchors each engine offers its own reading. The reading that
     agrees best with the other two (the medoid) wins. A timed reading (v2 or
     v3) wins ties; if Descript's text wins, it is timed by spreading it
     across the gap between the anchors.
  3. A window is flagged for human review when no two engines agree on its
     content words. Nothing is silently guessed.

Measured on one long-form job: large-v3 dropped two sentences of a sign-off
and invented whole phrases that neither other engine heard; this method
catches both kinds without hand-editing.

Fillers (uh, um, mm-hmm), stutter fragments ("a-and", "th-") and immediate
repeats are not votes; captions drop them.

  python transcripts_merge.py NAME v3.json v2.json descript.txt out_dir

Writes NAME.merged.json (timed words) and NAME.review.tsv (windows to confirm).
"""
import difflib
import json
import os
import re
import sys

FILLERS = {"uh", "um", "umm", "uhh", "er", "erm", "mm", "mmm", "hmm", "mhm", "mm-hmm", "uh-huh", "ah"}
EXPAND = {"wanna": ["want", "to"], "gonna": ["going", "to"], "gotta": ["got", "to"], "'cause": ["because"],
          "cause": ["because"], "ok": ["okay"], "kinda": ["kind", "of"], "sorta": ["sort", "of"],
          "percent": ["%"], "vs": ["versus"], "there's": ["there", "is"], "that's": ["that", "is"],
          "it's": ["it", "is"], "we're": ["we", "are"], "they're": ["they", "are"], "you're": ["you", "are"],
          "doesn't": ["does", "not"], "don't": ["do", "not"], "i'm": ["i", "am"], "what's": ["what", "is"],
          "we've": ["we", "have"], "i've": ["i", "have"], "can't": ["can", "not"], "won't": ["will", "not"],
          "isn't": ["is", "not"], "aren't": ["are", "not"], "'nother": ["another"], "nother": ["another"]}
NUMS = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6",
        "seven": "7", "eight": "8", "nine": "9", "ten": "10", "eleven": "11", "twelve": "12",
        "fifteen": "15", "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50", "sixty": "60",
        "hundred": "100"}
# US -> Australian spelling for display. Votes use the US form so spelling never counts as a disagreement.
AU = [("organization", "organisation"), ("prioritiz", "prioritis"), ("analyz", "analys"),
      ("defense", "defence"), ("behavior", "behaviour"), ("realiz", "realis"), ("recogniz", "recognis"),
      ("minimiz", "minimis"), ("maximiz", "maximis"), ("optimiz", "optimis"), ("democratiz", "democratis"),
      ("contextualiz", "contextualis"), ("utiliz", "utilis"), ("summariz", "summaris"),
      ("standardiz", "standardis"), ("favor", "favour"), ("labor", "labour"), ("modeling", "modelling"),
      ("traveling", "travelling"), ("fulfill", "fulfil")]
AU_WORD = [(r"\bcenter", "centre"), (r"\bcolor", "colour"), (r"\bCenter", "Centre"),
           (r"\btheater", "theatre"), (r"\bTheater", "Theatre"), (r"\bfiber", "fibre"), (r"\bFiber", "Fibre")]
PUNCT = ".,?!;:\"'()[]…"


def is_fragment(raw):
    r = raw.strip(PUNCT)
    if re.fullmatch(r"[A-Za-z]{1,4}-+", r):
        return True
    m = re.fullmatch(r"([A-Za-z]{1,2})-([A-Za-z]+)", r)
    return bool(m and m.group(2).lower().startswith(m.group(1).lower()))


def norm_tokens(text):
    out = []
    for raw in re.findall(r"[\w'%$\-\.&]+", text.lower().replace("’", "'")):
        if is_fragment(raw):
            continue
        t = raw.strip(".-'")
        if not t or t in FILLERS:
            continue
        m = re.fullmatch(r"(\d+)%", t)
        if m:
            out += [m.group(1), "%"]
            continue
        for p in ([q for q in t.split("-") if q] if "-" in t else [t]):
            p = NUMS.get(p, p)
            for us, au in AU:
                p = p.replace(au, us)
            out += EXPAND.get(p, [p])
    return out


def whisper_words(path):
    j = json.load(open(path, encoding="utf-8"))
    return [dict(text=w["word"].strip(), start=w["start"], end=w["end"], p=float(w.get("probability", 1)))
            for s in j.get("segments", []) for w in (s.get("words") or []) if w["word"].strip()]


def descript_words(path):
    ws = []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\[(\d+):(\d+):(\d+)\]\s*(.*)", line.strip())
        if m:
            t = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            for raw in m.group(4).split():
                ws.append(dict(text=raw, para=t))
    return ws


def tokenise(words):
    toks, idx = [], []
    for i, w in enumerate(words):
        for t in norm_tokens(w["text"]):
            if toks and t == toks[-1] and len(t) < 12:
                continue
            toks.append(t)
            idx.append(i)
    return toks, idx


def sim(a, b):
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    r = difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    blocks = difflib.SequenceMatcher(None, long_, short, autojunk=False).get_matching_blocks()
    cont = sum(x.size for x in blocks) / len(short)
    return max(r, cont * 0.9 if len(short) >= 2 else r)


def pair_map(ta, tb):
    m = {}
    for blk in difflib.SequenceMatcher(None, ta, tb, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k
    return m


def merge(name, v3p, v2p, dsp, out_dir):
    W3, W2, WD = whisper_words(v3p), whisper_words(v2p), descript_words(dsp)
    t3, i3 = tokenise(W3)
    t2, i2 = tokenise(W2)
    tD, iD = tokenise(WD)
    m32, m3D = pair_map(t3, t2), pair_map(t3, tD)
    anchors, last2, lastD = [], -1, -1
    for k in range(len(t3)):
        if k in m32 and k in m3D and m32[k] > last2 and m3D[k] > lastD:
            anchors.append((k, m32[k], m3D[k]))
            last2, lastD = m32[k], m3D[k]
    out, review = [], []
    used3, used2 = set(), set()

    def ts(x):
        return "%d:%05.2f" % (int(x // 60), x % 60)

    def emit(W, idx_list, used, src):
        for wi in sorted(set(idx_list)):
            if wi not in used:
                used.add(wi)
                w = W[wi]
                out.append(dict(text=w["text"], start=w["start"], end=w["end"], src=src))

    def txt(W, idx_list):
        return " ".join(W[j]["text"] for j in sorted(set(idx_list)))

    bounds = [(-1, -1, -1)] + anchors + [(len(t3), len(t2), len(tD))]
    for (a3, a2, aD), (b3, b2, bD) in zip(bounds, bounds[1:]):
        g3, g2, gD = t3[a3 + 1:b3], t2[a2 + 1:b2], tD[aD + 1:bD]
        if g3 or g2 or gD:
            s32, s3D, s2D = sim(g3, g2), sim(g3, gD), sim(g2, gD)
            score = {"v3": s32 + s3D, "v2": s32 + s2D, "descript": s3D + s2D}
            pick = sorted(score, key=lambda k: (-score[k], {"v2": 0, "v3": 1, "descript": 2}[k]))[0]
            best_pair = max(s32, s3D, s2D)
            t_lo = W3[i3[a3]]["end"] if a3 >= 0 else (W3[0]["start"] - 1 if W3 else 0)
            t_hi = W3[i3[b3]]["start"] if b3 < len(t3) else (W3[-1]["end"] + 1 if W3 else 0)
            if pick == "v3":
                emit(W3, i3[a3 + 1:b3], used3, "v3")
            elif pick == "v2":
                emit(W2, i2[a2 + 1:b2], used2, "v2")
            else:
                disp = [WD[j]["text"] for j in sorted(set(iD[aD + 1:bD]))]
                span, n = max(0.2, t_hi - t_lo), max(1, len(disp))
                for k, t in enumerate(disp):
                    out.append(dict(text=t, start=t_lo + span * k / n, end=t_lo + span * (k + 1) / n, src="descript"))
            content = [t for t in (g3 + g2 + gD) if len(t) > 2]
            row = (t_lo, pick, txt(W3, i3[a3 + 1:b3]), txt(W2, i2[a2 + 1:b2]), txt(WD, iD[aD + 1:bD]))
            if best_pair < 0.5 and content:
                review.append((row[0], "no majority") + row[1:])
            elif pick != "v3" and content and sim(g3, g2 if pick == "v2" else gD) < 0.999:
                review.append((row[0], "v3 outvoted") + row[1:])
        if b3 < len(t3):
            emit(W3, [i3[b3]], used3, "v3")
    # Keep the order the vote emitted, which is the spoken order. Sorting by
    # start time shuffled words wherever a Descript reading (timed by spreading
    # it across the gap) overlapped a timed neighbour: "say yes you when know
    # the CRO". Clamp timings forward instead.
    for k in range(1, len(out)):
        if out[k]["start"] < out[k - 1]["start"]:
            out[k]["start"] = out[k - 1]["start"] + 0.01
        if out[k]["end"] < out[k]["start"]:
            out[k]["end"] = out[k]["start"] + 0.05
    os.makedirs(out_dir, exist_ok=True)
    json.dump(dict(name=name, words=out), open(os.path.join(out_dir, name + ".merged.json"), "w", encoding="utf-8"),
              indent=0, ensure_ascii=False)
    with open(os.path.join(out_dir, name + ".review.tsv"), "w", encoding="utf-8") as f:
        f.write("time\tkind\tpicked\twhisper_v3\twhisper_v2\tdescript\n")
        for r in sorted(review):
            f.write("%s\t%s\t%s\t%s\t%s\t%s\n" % ((ts(r[0]),) + tuple(r[1:])))
    nm = sum(1 for r in review if r[1] == "no majority")
    print("%s: %d words out, %d anchors, %d windows outvoted v3, %d with no majority"
          % (name, len(out), len(anchors), len(review) - nm, nm))
    return out, review


def display_clean(words):
    """Caption-ready words: no fillers, fragments or stutter repeats; AU spelling."""
    res = []
    for w in words:
        raw = w["text"]
        core = raw.strip(PUNCT).lower()
        if not core or core in FILLERS or is_fragment(raw):
            continue
        if res and norm_tokens(raw) and norm_tokens(raw) == norm_tokens(res[-1]["text"]):
            res[-1] = dict(res[-1], text=raw, end=w["end"])
            continue
        t = raw
        for us, au in AU:
            t = t.replace(us, au).replace(us.capitalize(), au.capitalize())
        for pat, rep in AU_WORD:
            t = re.sub(pat, rep, t)
        # generic -ize -> -ise (organized, prioritizing, ...); stems of 3+ letters
        # skip size/prize/seize; capsize is the one real exception
        if not re.match(r"(?i)capsiz", t):
            t = re.sub(r"(?i)\b(\w{3,}?)iz(e|ed|es|ing|ation|ations|er|ers)\b",
                       lambda m: m.group(1) + ("is" if m.group(0)[len(m.group(1))].islower() else "IS")
                       + m.group(2), t)
        res.append(dict(w, text=t))
    return res


if __name__ == "__main__":
    merge(*sys.argv[1:6])
